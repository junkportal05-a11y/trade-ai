import asyncio
import schedule
import os
from datetime import datetime, timezone, timedelta

import db
import signals
from quant.correlation_matrix import CorrelationEngine
from quant.weekly_jobs import run_weekly_maintenance
from quant.market_regime import MarketRegimeClassifier
from quant.feature_attribution import FeatureAttributionEngine
from quant.filter_roi import FilterROIEngine
from quant.cost_engine import CostEngine
from quant.portfolio_simulator import PortfolioSimulator
from quant.capacity_simulator import CapacitySimulator
from quant.replay_engine import ReplayEngine
from quant.survivorship_validator import SurvivorshipValidator
from trade_quality import TradeQualityEngine
from ai_executive_committee import AIExecutiveCommittee

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

async def trading_agent_loop():
    """
    Autonomous Trading Agent Loop for Phase 3.
    - Runs every 30 min from 9:15 AM to 3:20 PM IST
    - Places max 2 paper trades
    - Auto-closes all at 3:20 PM
    """
    print("[trading_agent] Autonomous agent loop started.")

    correlation_engine = CorrelationEngine()
    ai_exec = AIExecutiveCommittee()
    last_scan_bucket = None

    # Instantiate additional quant utilities (may be used later)
    filter_roi_engine = FilterROIEngine()
    feature_attrib_engine = FeatureAttributionEngine()
    cost_engine = CostEngine()
    market_regime_cls = MarketRegimeClassifier()
    portfolio_sim = PortfolioSimulator()
    capacity_sim = CapacitySimulator()
    replay_engine = ReplayEngine()
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
                        run_weekly_maintenance()
                    except Exception as e:
                        print(f"[trading_agent] Weekly maintenance error: {e}")
                print("[trading_agent] Market closed (weekend). Next check in 1 hour.")
                await asyncio.sleep(3600)
                continue

            minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
            start_minutes = 9 * 60 + 15
            end_minutes = 15 * 60 + 20  # 3:20 PM

            # Auto-square off at 3:20 PM
            if minutes_since_midnight == end_minutes:
                print("[trading_agent] 3:20 PM reached. Executing auto-square off.")
                _square_off_all(now_ist)
                await asyncio.sleep(60)  # prevent multiple triggers
                continue

            if minutes_since_midnight > end_minutes or minutes_since_midnight < start_minutes:
                print("[trading_agent] Market closed. Next check in 30 minutes.")
                await asyncio.sleep(1800)
                continue

            # We are within market hours
            # 1. Monitor open trades (Every 2 mins theoretically, but resolver handles this async).
            # The prediction_resolver_worker already polls every N seconds, so agent doesn't need to reinvent wheel for SL/TP.

            # 2. Check how many open positions we have
            predictions = db.get_predictions()
            open_positions = [p for p in predictions if p.get("status") == "PENDING"]

            if len(open_positions) >= MAX_CONCURRENT_TRADES:
                print("[trading_agent] Max positions ({MAX_CONCURRENT_TRADES}) reached. Skipping scan.")
                await asyncio.sleep(1800)  # Wait 30 mins before next scan
                continue

            # 3. Time to scan (e.g., every 30 mins)
            current_bucket = minutes_since_midnight // 30
            if last_scan_bucket is None or current_bucket > last_scan_bucket:
                last_scan_bucket = current_bucket

                # Check Correlation Matrix freshness
                if correlation_engine.last_built_date:
                    days_old = (now_ist.date() - correlation_engine.last_built_date).days
                    if days_old > 14:
                        print("[WARNING] Correlation matrix is {days_old} days old. It should be rebuilt weekly.")
                else:
                    print("[WARNING] Correlation matrix has no built date.")

                print("[trading_agent] Running 30-min scan. Current time: {now_ist.strftime('%H:%M')}")
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

                    # Wire AI Executive Committee (TradingAgents LLM Debate)
                    ai_decision = ai_exec.evaluate_trade(sig["symbol"], sig)
                    if not ai_decision.get("approved", False):
                        print(f"[trading_agent] AI Executive Committee rejected trade for {sig['symbol']}: {ai_decision.get('reasoning')}")
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

def _square_off_all(now_ist):
    predictions = db.get_predictions()
    pending = [p for p in predictions if p.get("status") == "PENDING"]

    feed = get_angelone_feed()

    async def fetch_and_resolve(pred):
        """Fetch live quote and resolve prediction using quote executor."""
        loop = asyncio.get_event_loop()

        if feed.is_authorized():
            quotes = await loop.run_in_executor(
                quote_executor,
                lambda: feed.get_live_quotes([pred["symbol"]])
            )
            live_quote = quotes.get(pred["symbol"])
            live_price = live_quote.get("price", pred["entry_price"])
        else:
            live_price = pred["entry_price"]

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
    loop = asyncio.get_event_loop()
    tasks = [fetch_and_resolve(pred) for pred in pending]
    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

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