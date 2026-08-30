import asyncio
import schedule
import os
from datetime import datetime, timezone, timedelta
from app.core.constants import (
    NSE_OPEN_HOUR,
    NSE_OPEN_MINUTE,
    NSE_CLOSE_HOUR,
    NSE_CLOSE_MINUTE,
    IST_OFFSET_HOURS,
    IST_OFFSET_MINUTES,
)

import db
import signals
from quant.correlation_matrix import CorrelationEngine
from quant.weekly_jobs import run_weekly_tasks
from quant.market_regime import MarketRegimeClassifier
from quant.cost_engine import CostEngine
from quant.survivorship_validator import SurvivorshipValidator
from trade_quality import TradeQualityEngine

from app.core.executors import (
    scan_executor,
    quote_executor,
    resolver_executor,
    governance_executor,
    trading_executor,
)

MAX_CONCURRENT_TRADES = 2
MIN_AGENT_CONFIDENCE = 72

def refresh_angelone_session():
    """
    Refresh AngelOne authentication session scheduled via daily job.
    This function handles session validity check and auto-refresh logic.
    """
    try:
        feed = AngelOneFeed()
        if feed.is_session_valid():
            print("[trading_agent] AngelOne session valid, skipping refresh.")
            return True
        else:
            print("[trading_agent] Refreshing AngelOne session...")
            success = feed.auto_login()
            if success:
                print("[trading_agent] AngelOne session refreshed successfully.")
            else:
                print("[trading_agent] Failed to refresh AngelOne session.")
            return success
    except Exception as e:
        print(f"[trading_agent] Session refresh error: {e}")
        return False

# Schedule daily session refresh at 8:30 AM IST (market opens at 9:15 AM IST)
schedule.every().day.at('08:30').do(refresh_angelone_session)


# ─── Extracted scan logic for reuse by loop & /api/agent/trigger-scan ───
async def run_scan_cycle() -> list[dict]:
    """Run one scan iteration and return list of signal dicts."""
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    # Outside market hours → no trades
    minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
    start_minutes = 9 * 60 + 15
    end_minutes = 15 * 60 + 20
    if minutes_since_midnight < start_minutes or minutes_since_midnight > end_minutes:
        return []

    # Check bot state
    state = db.get_bot_state()
    if state not in ("RUNNING",):
        return []

    # Run scan
    results = signals.run_scan(symbols=signals.NSE_WATCHLIST)

    # Apply same TQS / Correlation filters as trading_agent_loop
    filtered = []
    open_positions = [p for p in db.get_predictions() if p.get("status") == "PENDING"]

    for sig in results:
        if sig.get("signal") not in ("BUY", "SELL"):
            continue
        if len(open_positions) >= MAX_CONCURRENT_TRADES:
            break

        # TradeQualityEngine check
        tqs = TradeQualityEngine.calculate_tqs(
            confidence_score=sig.get("confidence", 0),
            is_long=(sig["signal"] == "BUY"),
            regime=sig.get("market_regime_snapshot", "UNCLEAR"),
            volatility=sig.get("atr", 0.0),
            volume_expansion=sig.get("vol_ratio", 1.0),
        )
        if tqs["classification"] not in ("INTRADAY_CANDIDATE", "ELITE_CANDIDATE"):
            continue

        # CorrelationEngine check
        open_symbols = [p["symbol"] for p in open_positions]
        correlation_engine = CorrelationEngine()
        if not correlation_engine.check_trade_allowed(sig["symbol"], open_symbols):
            continue

        filtered.append(sig)

    return filtered


async def trading_agent_loop():
    """
    Autonomous Trading Agent Loop for Phase 3.
    - Runs every 30 min from 9:15 AM to 3:20 PM IST
    - Places max 2 paper trades
    - Auto-closes all at 3:20 PM
    """
    print("[trading_agent] Autonomous agent loop started.")

    correlation_engine = CorrelationEngine()
    last_scan_bucket = None

    # Instantiate additional quant utilities (may be used later)
    cost_engine = CostEngine()
    market_regime_cls = MarketRegimeClassifier()
    survivor_validator = SurvivorshipValidator()

    while True:
        try:
            from app.core.worker_health import beat
            beat("agent")
            # Run scheduled tasks (e.g., daily session refresh at 8:30 AM IST)
            schedule.run_pending()

            # ── Bot state gate (RUNNING / PAUSED / STOPPED) ──
            state = db.get_bot_state()
            if state == "STOPPED":
                # Bot halted: skip scanning, keep loop alive to detect RUNNING.
                await asyncio.sleep(30)
                continue
            if state == "PAUSED":
                # Paused: skip new scans but keep monitoring open positions.
                # The prediction_resolver_worker polls SL/TP, so just wait.
                await asyncio.sleep(30)
                continue

            now_utc = datetime.now(timezone.utc)
            now_ist = now_utc + timedelta(hours=5, minutes=30)

            # Weekend check — run weekly maintenance on Sunday night (hour 21-22 IST)
            if now_ist.weekday() >= 5:
                if now_ist.weekday() == 6 and 21 <= now_ist.hour < 22:
                    # Sunday night: run weekly maintenance jobs
                    print("[trading_agent] Sunday night maintenance window. Running weekly jobs.")
                    try:
                        run_weekly_tasks()
                    except Exception as e:
                        print(f"[trading_agent] Weekly maintenance error: {e}")
                print("[trading_agent] Market closed (weekend). Checking again in 30s.")
                await asyncio.sleep(30)
                continue

            minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
            start_minutes = 9 * 60 + 15
            end_minutes = 15 * 60 + 20  # 3:20 PM

            # Auto-square off at 3:20 PM
            if minutes_since_midnight == end_minutes:
                print("[trading_agent] 3:20 PM reached. Executing auto-square off.")
                await _square_off_all(now_ist)
                await asyncio.sleep(60)  # prevent multiple triggers
                continue

            if minutes_since_midnight > end_minutes or minutes_since_midnight < start_minutes:
                print("[trading_agent] Market closed. Next check in 30 seconds.")
                await asyncio.sleep(30)
                continue

            # We are within market hours
            # 1. Monitor open trades (Every 2 mins theoretically, but resolver handles this async).
            # The prediction_resolver_worker already polls every N seconds, so agent doesn't need to reinvent wheel for SL/TP.

            # 2. Check how many open positions we have
            predictions = db.get_predictions()
            open_positions = [p for p in predictions if p.get("status") == "PENDING"]

            if len(open_positions) >= MAX_CONCURRENT_TRADES:
                print(f"[trading_agent] Max positions ({MAX_CONCURRENT_TRADES}) reached. Skipping scan.")
                await asyncio.sleep(30)
                continue

            # 3. Time to scan (e.g., every 30 mins)
            current_bucket = minutes_since_midnight // 30
            if last_scan_bucket is None or current_bucket > last_scan_bucket:
                last_scan_bucket = current_bucket

                # Check Correlation Matrix freshness
                if correlation_engine.last_built_date:
                    days_old = (now_ist.date() - correlation_engine.last_built_date).days
                    if days_old > 14:
                        print(f"[WARNING] Correlation matrix is {days_old} days old. It should be rebuilt weekly.")
                else:
                    print("[WARNING] Correlation matrix has no built date.")

                print(f"[trading_agent] Running 30-min scan. Current time: {now_ist.strftime('%H:%M')}")
                results = signals.run_scan(symbols=signals.NSE_WATCHLIST)

                for sig in results:
                    if sig.get("signal") not in ("BUY", "SELL"):
                        continue

                    if len(open_positions) >= MAX_CONCURRENT_TRADES:
                        break

                    # Wire TradeQualityEngine
                    tqs = TradeQualityEngine.calculate_tqs(
                        confidence_score=sig.get("confidence", 0),
                        is_long=(sig["signal"] == "BUY"),
                        regime=sig.get("market_regime_snapshot", "UNCLEAR"),
                        volatility=sig.get("atr", 0.0),
                        volume_expansion=sig.get("vol_ratio", 1.0)
                    )

                    if tqs["classification"] not in ("INTRADAY_CANDIDATE", "ELITE_CANDIDATE"):
                        continue

                    # Wire CorrelationEngine
                    open_symbols = [p["symbol"] for p in open_positions]
                    if not correlation_engine.check_trade_allowed(sig["symbol"], open_symbols):
                        print(f"[trading_agent] Blocked trade for {sig['symbol']} due to high correlation.")
                        continue

                    # Place paper trade
                    prediction_id = db.add_prediction(_build_prediction_payload(sig))

                    db.add_journal_entry(_build_journal_payload(sig))

                    print(f"[trading_agent] Placed paper trade for {sig['symbol']} at {sig['price']}")
                    open_positions.append({"id": prediction_id, **sig})

            await asyncio.sleep(60)  # check time again in 1 min

        except Exception as e:
            print(f"[trading_agent] Error: {e}")
            await asyncio.sleep(60)

async def _square_off_all(now_ist):
    predictions = db.get_predictions()
    pending = [p for p in predictions if p.get("status") == "PENDING"]

    feed = get_angelone_feed()

    async def fetch_and_resolve(pred):
        """Fetch live quote and resolve prediction using quote executor."""
        loop = asyncio.get_running_loop()

        if feed.is_authorized():
            quotes = await loop.run_in_executor(
                quote_executor,
                lambda: feed.get_live_quotes([pred["symbol"]])
            )
            live_quote = quotes.get(pred["symbol"])
            if not live_quote:
                print(f"[trading_agent] No live quote for {pred['symbol']} during square-off, skipping")
                return
            live_price = live_quote.get("price", pred["entry_price"])
        else:
            raise RuntimeError(f"[trading_agent] Cannot square off: AngelOne feed not authorized")

        entry_price = float(pred["entry_price"])

        if pred["prediction_type"] in ["BUY", "BULLISH"]:
            pnl_inr = (live_price - entry_price) * pred.get("position_size", 1)
        else:
            pnl_inr = (entry_price - live_price) * pred.get("position_size", 1)

        pnl_pct = (pnl_inr / (entry_price * pred.get("position_size", 1))) * 100 if entry_price > 0 else 0

        await loop.run_in_executor(
            resolver_executor,
            lambda: db.resolve_prediction(
                pred_id=pred["id"],
                actual_outcome=live_price,
                status="TIMEOUT",
                exit_price=live_price,
                holding_time_minutes=0,
                pnl_pct=round(pnl_pct, 2),
                pnl_inr=round(pnl_inr, 2),
                r_multiple=0,
                resolution_reason="SQUARE_OFF_3_20",
                discard_reason="SQUARE_OFF_3_20",
            )
        )
        print(f"[trading_agent] Auto-closed {pred['symbol']} at {live_price}")

    # Run all square-offs concurrently
    tasks = [fetch_and_resolve(pred) for pred in pending]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

def _build_prediction_payload(sig: dict) -> dict:
    """Build prediction payload for db.add_prediction."""
    return {
        "symbol": sig["symbol"],
        "entry_price": sig.get("price"),
        "target_price": sig.get("target"),
        "stop_loss": sig.get("stop_loss"),
        "confidence_score": sig.get("confidence", 0),
        "rsi": sig.get("rsi", 50),
        "macd": sig.get("macd", 0),
        "adx": sig.get("adx", 0),
        "sector": sig.get("sector", "NSE"),
        "market_cap": sig.get("market_cap", 0),
        "volume_ratio": sig.get("vol_ratio", 1.0),
        "vwap_distance": sig.get("vwap_distance", 0.0),
        "atr": sig.get("atr", 0.0),
        "news_score": sig.get("news_score", 0.0),
        "market_breadth": sig.get("market_breadth", 0.0),
        "sector_strength": sig.get("sector_strength", 0.0),
        "nifty_trend": sig.get("nifty_trend", "FLAT"),
        "setup_type": sig.get("setup_type", "UNKNOWN"),
        "market_regime_snapshot": sig.get("market_regime_snapshot", "UNKNOWN"),
        "risk_amount": sig.get("risk_amount", 0.0),
        "confidence_probability": sig.get("confidence_probability", 0.5),
        "regime_score": sig.get("regime_score", 0.0),
        "sector_score": sig.get("sector_score", 0.0),
        "volume_score": sig.get("volume_score", 0.0),
        "rs_score": sig.get("rs_score", 0.0),
        "trade_quality_score": sig.get("trade_quality_score", 0.0),
        "correlation_score": sig.get("correlation_score", 0.0),
        "signal_time": sig.get("signal_time", datetime.now(timezone.utc).isoformat()),
        "order_time": sig.get("order_time", datetime.now(timezone.utc).isoformat()),
    }

def _build_journal_payload(sig: dict) -> dict:
    """Build journal entry payload for db.add_journal_entry."""
    return {
        "symbol": sig["symbol"],
        "direction": sig.get("signal"),
        "entry_price": sig.get("price"),
        "exit_price": None,
        "qty": 1,
        "entry_date": datetime.now(timezone.utc).isoformat(),
        "reason": sig.get("reasoning", ""),
        "emotion": "Calm",
        "status": "OPEN",
        "pnl": None,
    }


def resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price):
    """
    Standalone decision function for SL/TP resolution with pessimistic priority.
    Returns tuple (status, reason) where:
    - status: "STOP_HIT", "TARGET_HIT", or None
    - reason: "STOP_LOSS_HIT", "TARGET_HIT", or None
    """
    if direction in ("BUY", "BULLISH"):
        hit_sl = (current_price <= stop_loss > 0)
        hit_tp = (current_price >= target_price > 0)
    elif direction in ("SELL", "BEARISH"):
        hit_sl = (current_price >= stop_loss > 0)
        hit_tp = (current_price <= target_price > 0)
    else:
        hit_sl = hit_tp = False

    if hit_sl:
        return ("STOP_HIT", "STOP_LOSS_HIT")
    elif hit_tp:
        return ("TARGET_HIT", "TARGET_HIT")
    else:
        return (None, None)


async def prediction_resolver_worker():
    """
    Background worker that continuously polls pending predictions to resolve SL/TP hits.
    Emits worker_health.beat("resolver") on every iteration.
    """
    print("[prediction_resolver] Resolver worker loop started.")
    while True:
        try:
            # Read polling interval from environment
            poll_seconds = int(os.getenv("RESOLVER_POLL_SECONDS", "15"))

            # Emit heartbeat
            from app.core.worker_health import beat
            beat("resolver")

            # Market hours gate
            from app.services.market_hours import is_nse_market_open
            if not is_nse_market_open():
                print("[prediction_resolver] Market closed, skipping resolve check")
                await asyncio.sleep(poll_seconds)
                continue

            loop = asyncio.get_running_loop()
            predictions = await loop.run_in_executor(resolver_executor, db.get_predictions)
            pending = [p for p in (predictions or []) if p.get("status") == "PENDING"]

            if pending:
                from angelone_feed import get_angelone_feed
                feed = get_angelone_feed()
                if not feed.is_authorized():
                    print("[prediction_resolver] AngelOne feed not authorized, cannot resolve predictions")
                    await asyncio.sleep(poll_seconds)
                    continue
                symbols = list({p["symbol"] for p in pending})
                quotes = await loop.run_in_executor(
                    quote_executor, lambda: feed.get_live_quotes(symbols)
                )
                if not quotes:
                    print("[prediction_resolver] No live quotes returned from broker")
                    await asyncio.sleep(poll_seconds)
                    continue
                for pred in pending:
                    sym = pred["symbol"]
                    live_quote = quotes.get(sym)
                    if not live_quote:
                        print(f"[prediction_resolver] No live quote for {sym}, skipping")
                        continue
                        current_price = live_quote.get("price", 0.0)
                        entry_price = float(pred.get("entry_price", 0.0))
                        stop_loss = float(pred.get("stop_loss", 0.0))
                        target_price = float(pred.get("target_price", 0.0))
                        direction = pred.get("prediction_type", "BUY")

                        # Pessimistic priority rule: STOP_LOSS wins if both hit
                        if direction in ("BUY", "BULLISH"):
                            hit_sl = (current_price <= stop_loss > 0)
                            hit_tp = (current_price >= target_price > 0)
                        elif direction in ("SELL", "BEARISH"):
                            hit_sl = (current_price >= stop_loss > 0)
                            hit_tp = (current_price <= target_price > 0)
                        else:
                            hit_sl = hit_tp = False

                        status = None
                        reason = None
                        if hit_sl:
                            status = "STOP_HIT"
                            reason = "STOP_LOSS_HIT"
                        elif hit_tp:
                            status = "TARGET_HIT"
                            reason = "TARGET_HIT"

                        if status and reason:
                            pnl_inr = (current_price - entry_price) if direction in ("BUY", "BULLISH") else (entry_price - current_price)
                            pnl_pct = (pnl_inr / entry_price) * 100 if entry_price > 0 else 0

                            await loop.run_in_executor(
                                resolver_executor,
                                lambda: db.resolve_prediction(
                                    pred_id=pred["id"],
                                    actual_outcome=current_price,
                                    status=status,
                                    exit_price=current_price,
                                    holding_time_minutes=15,
                                    pnl_pct=round(pnl_pct, 2),
                                    pnl_inr=round(pnl_inr, 2),
                                    r_multiple=1.5 if hit_tp else -1.0,
                                    resolution_reason=reason,
                                    discard_reason=reason,
                                )
                            )
                            print(f"[prediction_resolver] Resolved {sym}: {reason} at {current_price}")
        except Exception as e:
            print(f"[prediction_resolver] Error: {e}")

        # Use dynamic poll interval
        await asyncio.sleep(poll_seconds)