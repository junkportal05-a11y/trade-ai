import asyncio
import schedule
import os
import time
from datetime import datetime, timezone, timedelta

import db
import signals
from quant.correlation_matrix import CorrelationEngine
from quant.weekly_jobs import run_weekly_tasks
from quant.market_regime import MarketRegimeClassifier
from quant.cost_engine import CostEngine
from quant.survivorship_validator import SurvivorshipValidator
from trade_quality import TradeQualityEngine

from app.core.executors import (
    quote_executor,
    resolver_executor,
)
from app.core.worker_state import any_degraded, get_degraded_workers
from app.core.logging import logger

MAX_CONCURRENT_TRADES = 2
MIN_AGENT_CONFIDENCE = 72
IST_OFFSET = timedelta(hours=5, minutes=30)

# TAR-20 Task 8: paper-trading data honesty. Only signals derived from real
# market-data tiers may enter the paper loop. 'synthetic'/'seed' — and any
# untagged/unknown source — are treated as simulated and NEVER traded: a
# synthetic fallback candle series must not become a paper trade record.
REAL_DATA_SOURCES = frozenset({"angelone", "yfinance", "last-good"})


def prediction_start_utc(raw_prediction_date):
    """Parse a stored prediction_date into an aware UTC datetime, or None.

    db.add_prediction stores naive IST strings ("YYYY-MM-DD HH:MM:SS");
    some legacy rows and test fixtures carry ISO strings with an offset.
    """
    if not raw_prediction_date:
        return None
    candidate = str(raw_prediction_date).strip()
    parsed = None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                parsed = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(IST_OFFSET))
    return parsed.astimezone(timezone.utc)


def holding_minutes_from_prediction_date(raw_prediction_date, fallback: float = 0.0) -> float:
    start_utc = prediction_start_utc(raw_prediction_date)
    if start_utc is None:
        return fallback
    minutes = (datetime.now(timezone.utc) - start_utc).total_seconds() / 60.0
    return max(0.0, minutes)

def refresh_angelone_session():
    """
    Refresh AngelOne authentication session scheduled via daily job.
    This function handles session validity check and auto-refresh logic.
    """
    try:
        from angelone_feed import AngelOneFeed

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
    Autonomous Trading Agent Loop.
    PHASE 1: PAPER ONLY — this loop places paper trades exclusively
    (order_mode is paper on every prediction); no live orders originate here.
    - Runs every 30 min from 9:15 AM to 3:20 PM IST
    - Places max 2 paper trades
    - Auto-closes all at 3:20 PM
    """
    print("[trading_agent] Autonomous agent loop started.")

    correlation_engine = CorrelationEngine()
    last_scan_bucket = None
    last_scan_date = None       # IST date of the last scan — reset bucket per day
    squared_off_today = False   # EOD square-off guard (one per day)

    # Track degraded workers logging state
    _last_logged_degraded: frozenset[str] | None = None
    _last_log_time: float = 0.0

    # Instantiate additional quant utilities (may be used later)
    CostEngine()
    market_regime_cls = MarketRegimeClassifier()
    SurvivorshipValidator()

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

            # Block new trades if any background worker is degraded
            if any_degraded():
                degraded = get_degraded_workers()
                degraded_keys = frozenset(degraded.keys())
                now = time.monotonic()
                if degraded_keys != _last_logged_degraded or now - _last_log_time >= 300:
                    logger.warning("Skipping new trades - degraded workers: %s", degraded)
                    _last_logged_degraded = degraded_keys
                    _last_log_time = now
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

            # New trading day: reset the scan bucket so the 9:15 bucket
            # (18) isn't swallowed by yesterday's last bucket (32).
            if last_scan_date != now_ist.date():
                last_scan_date = now_ist.date()
                last_scan_bucket = None
                squared_off_today = False
                # Refresh the Nifty-50 macro regime once per trading day.
                try:
                    market_regime_cls.load_data(force_refresh=True)
                    print("[trading_agent] Macro regime data refreshed for the new session.")
                except Exception as regime_exc:
                    print(f"[trading_agent] Macro regime refresh failed: {regime_exc}")

            # Auto-square off at/after 3:20 PM (exact-minute equality can be
            # straddled by a long scan iteration and skip the day entirely)
            if minutes_since_midnight >= end_minutes:
                if not squared_off_today:
                    print("[trading_agent] 3:20 PM reached. Executing auto-square off.")
                    await _square_off_all(now_ist)
                    squared_off_today = True
                await asyncio.sleep(60)
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

            # Institutional risk engine: tighten stops on in-the-money trades
            # with a 1.5x ATR trail before any new risk is added.
            if open_positions:
                await _update_trailing_stops(open_positions)
                predictions = db.get_predictions()
                open_positions = [p for p in predictions if p.get("status") == "PENDING"]

            # NIFTY 50 macro-regime gate: long momentum breakouts only when the
            # index trades above its 50-day EMA; otherwise mean-reversion
            # dip-buys (oversold setups) or cash preservation.
            macro_regime = market_regime_cls.classify_regime()
            nifty_above_ema50 = macro_regime.get("nifty_above_ema50")

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

                print(
                    f"[trading_agent] Running 30-min scan. Current time: {now_ist.strftime('%H:%M')} | "
                    f"Macro regime: {macro_regime.get('regime')} | "
                    f"NIFTY>EMA50: {nifty_above_ema50}"
                )
                results = signals.run_scan(symbols=signals.NSE_WATCHLIST)

                for sig in results:
                    if sig.get("signal") not in ("BUY", "SELL"):
                        continue

                    # Macro trend gate: unconditionally block non-oversold longs
                    # when NIFTY 50 trades below its 50-day EMA (trend vs mean
                    # reversion switching). Oversold dip-buys (RSI < 35) remain
                    # the mean-reversion lane; shorts (anti-momentum) unaffected.
                    if (
                        sig.get("signal") == "BUY"
                        and nifty_above_ema50 is not None
                        and not nifty_above_ema50
                        and sig.get("rsi", 50) >= 35
                    ):
                        print(
                            f"[trading_agent] Macro gate: NIFTY 50 below 50-day EMA — "
                            f"blocked long momentum {sig['symbol']} (RSI {sig.get('rsi', 50):.0f})"
                        )
                        continue

                    # TAR-20 Task 8: synthetic/simulated signals never become
                    # paper trades (fail-closed: missing or unknown data_source
                    # counts as simulated).
                    if sig.get("data_source") not in REAL_DATA_SOURCES:
                        logger.info(
                            "[trading_agent] Skipping %s for %s — data_source=%r is not a real "
                            "market-data tier; synthetic/simulated signals never trade",
                            sig.get("signal"), sig.get("symbol"), sig.get("data_source"),
                        )
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
                    try:
                        prediction_id = db.add_prediction(_build_prediction_payload(sig))
                    except Exception as insert_exc:
                        logger.error(
                            "[trading_agent] Failed to insert prediction for %s: %s",
                            sig.get("symbol"), insert_exc, exc_info=True,
                        )
                        continue

                    db.add_journal_entry(_build_journal_payload(sig))

                    print(f"[trading_agent] Placed paper trade for {sig['symbol']} at {sig['price']}")
                    open_positions.append({"id": prediction_id, **sig})

            await asyncio.sleep(60)  # check time again in 1 min

        except Exception as e:
            logger.error("[trading_agent] Trading loop error: %s", e, exc_info=True)
            await asyncio.sleep(60)

# ── Institutional risk engine: dynamic ATR trailing stops ────────────────────

TRAIL_ACTIVATION_ATR = 1.0   # activate the trail once the trade is ~1 ATR in favor
TRAIL_ATR_MULT = 1.5         # mandated: 1.5x ATR trailing stop


def _propose_trailing_stop(pred: dict, current_price: float):
    """Compute a tightened stop for an in-the-money paper trade.

    The trail only ever tightens (ratchet): it activates when price has moved
    >= TRAIL_ACTIVATION_ATR in the trade's favor and follows price at
    TRAIL_ATR_MULT * ATR. Returns the new stop or None when unchanged.

    `pred` — db predictions_history row; entry/stop/atr are floats, activity
    direction from prediction_type ("BUY"/"BULLISH" = long).
    """
    try:
        atr = abs(float(pred.get("atr") or 0.0))
        entry = float(pred.get("entry_price") or 0.0)
        stop = float(pred.get("stop_loss") or 0.0)
        price = float(current_price)
    except (TypeError, ValueError):
        return None
    if atr <= 0 or entry <= 0 or price <= 0:
        return None

    is_long = pred.get("prediction_type", "BUY").upper() in ("BUY", "BULLISH")
    if is_long:
        if price < entry + TRAIL_ACTIVATION_ATR * atr:
            return None
        trail = price - TRAIL_ATR_MULT * atr
        if trail > stop:
            return round(trail, 2)
        return None
    else:
        # Short: trail activates below the entry, stop trails above price and
        # can only ratchet down. Valid even when the legacy stop is 0.
        if price > entry - TRAIL_ACTIVATION_ATR * atr:
            return None
        trail = price + TRAIL_ATR_MULT * atr
        if stop <= 0 or trail < stop - 1e-9:
            return round(trail, 2)
        return None


async def _update_trailing_stops(open_predictions: list) -> int:
    """Fetch live quotes in bulk and tighten stops for winning open trades."""
    if not open_predictions:
        return 0

    from angelone_feed import get_angelone_feed
    feed = get_angelone_feed()
    # No authorized feed: prediction_resolver_worker still polls the static
    # SL/TP; trailing simply has no current price to trail against.
    if not feed.is_authorized():
        return 0

    symbols = sorted({p.get("symbol") for p in open_predictions if p.get("symbol")})
    if not symbols:
        return 0

    loop = asyncio.get_running_loop()
    try:
        quotes = await loop.run_in_executor(
            quote_executor, lambda: feed.get_live_quotes(symbols)
        )
    except Exception as e:
        logger.warning("[trading_agent] Trailing-stop quote fetch failed: %s", e)
        return 0

    updates: list[tuple] = []
    for pred in open_predictions:
        quote = (quotes or {}).get(pred.get("symbol"))
        if quote is None:
            continue
        if isinstance(quote, dict):
            live_price = float(quote.get("price") or 0.0)
        else:
            live_price = float(getattr(quote, "price", 0.0) or 0.0)
        if live_price <= 0:
            continue
        new_stop = _propose_trailing_stop(pred, live_price)
        if new_stop is not None:
            updates.append((pred["id"], new_stop))
            logger.info(
                "[trading_agent] Trailing stop tightened for %s (id=%s): %s -> %.2f",
                pred.get("symbol"), pred.get("id"), pred.get("stop_loss"), new_stop,
            )

    if updates:
        await loop.run_in_executor(
            resolver_executor, lambda: db.update_prediction_stops(updates)
        )
    return len(updates)


async def _square_off_all(now_ist):
    predictions = db.get_predictions()
    pending = [p for p in predictions if p.get("status") == "PENDING"]
    if not pending:
        return

    from angelone_feed import get_angelone_feed
    feed = get_angelone_feed()

    async def fetch_and_resolve(pred):
        """Fetch live quote and resolve prediction using quote executor."""
        loop = asyncio.get_running_loop()

        if not feed.is_authorized():
            logger.error("[trading_agent] Cannot square off %s: AngelOne feed not authorized", pred.get("symbol"))
            return
        quotes = await loop.run_in_executor(
            quote_executor,
            lambda: feed.get_live_quotes([pred["symbol"]])
        )
        live_quote = quotes.get(pred["symbol"])
        if not live_quote:
            logger.error("[trading_agent] No live quote for %s during square-off, leaving open for next cycle", pred["symbol"])
            return
        live_price = live_quote.get("price", pred["entry_price"])

        entry_price = float(pred["entry_price"])
        stop_loss = float(pred.get("stop_loss") or 0.0)
        position_size = float(pred.get("position_size") or 1.0)
        is_long = pred["prediction_type"] in ["BUY", "BULLISH"]

        if is_long:
            price_move = live_price - entry_price
            risk_per_share = entry_price - stop_loss
        else:
            price_move = entry_price - live_price
            risk_per_share = stop_loss - entry_price

        r_multiple = round(price_move / abs(risk_per_share), 2) if risk_per_share != 0 else 0.0
        pnl_inr = price_move * position_size
        pnl_pct = (price_move / entry_price) * 100 if entry_price > 0 else 0
        holding_time_minutes = holding_minutes_from_prediction_date(pred.get("prediction_date"), fallback=0.0)

        await loop.run_in_executor(
            resolver_executor,
            lambda: db.resolve_prediction(
                pred_id=pred["id"],
                actual_outcome="SQUARE_OFF",
                status="SQUARE_OFF",
                exit_price=live_price,
                holding_time_minutes=round(holding_time_minutes, 2),
                pnl_pct=round(pnl_pct, 2),
                pnl_inr=round(pnl_inr, 2),
                r_multiple=r_multiple,
                resolution_reason="SQUARE_OFF_3_20",
            )
        )
        logger.info(
            "[trading_agent] Auto-closed %s at %s (qty=%s, r=%s, hold=%.1fm, pnl=%s INR)",
            pred["symbol"], live_price, position_size, r_multiple,
            holding_time_minutes, round(pnl_inr, 2),
        )

    # Run all square-offs concurrently; per-row errors are logged, not fatal
    tasks = [fetch_and_resolve(pred) for pred in pending]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for pred, result in zip(pending, results):
        if isinstance(result, BaseException):
            logger.error(
                "[trading_agent] Square-off failed for %s (id=%s): %s",
                pred.get("symbol"), pred.get("id"), result,
            )

def _build_prediction_payload(sig: dict) -> dict:
    """Build prediction payload for db.add_prediction."""
    return {
        "symbol": sig["symbol"],
        "prediction_type": "BULLISH" if sig.get("signal", "BUY") == "BUY" else "BEARISH",
        "entry_price": sig.get("price"),
        "target_price": sig.get("target"),
        "stop_loss": sig.get("stop_loss"),
        "confidence_score": sig.get("confidence", 0),
        "rsi": sig.get("rsi", 50),
        "macd": sig.get("macd", 0),
        "macd_hist": sig.get("macd_hist", 0),
        "position_size": sig.get("position_size", 1),
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
        "order_mode": "paper",
        # TAR-20 Task 8: which feed tier produced the candles behind this
        # signal (angelone|yfinance|last-good|synthetic|seed|None-unknown).
        "data_source": sig.get("data_source"),
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
        # TAR-20 Task 8: feed tier of the data the agent acted on (audit trail).
        "data_source": sig.get("data_source"),
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
                    pred_id = pred.get("id")
                    live_quote = quotes.get(sym)
                    if not live_quote:
                        logger.warning(f"[prediction_resolver] No live quote for {sym}, skipping")
                        continue
                    try:
                        current_price = live_quote.get("price", 0.0)
                        entry_price = float(pred.get("entry_price", 0.0))
                        stop_loss = float(pred.get("stop_loss", 0.0))
                        target_price = float(pred.get("target_price", 0.0))
                        direction = pred.get("prediction_type", "BUY")
                        position_size = float(pred.get("position_size", 1.0))

                        # Calculate holding time from prediction_date (stored as naive IST: "YYYY-MM-DD HH:MM:SS")
                        holding_minutes = holding_minutes_from_prediction_date(
                            pred.get("prediction_date"), fallback=15.0
                        )

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
                            try:
                                # Price move per share
                                if direction in ("BUY", "BULLISH"):
                                    price_move = current_price - entry_price
                                    risk_per_share = entry_price - stop_loss
                                else:
                                    price_move = entry_price - current_price
                                    risk_per_share = stop_loss - entry_price

                                # r_multiple = price move per share / risk per share
                                if risk_per_share == 0:
                                    logger.warning(f"[prediction_resolver] Zero risk_per_share for {sym} (id={pred_id}), setting r_multiple=0")
                                    r_multiple = 0.0
                                else:
                                    r_multiple = round(price_move / abs(risk_per_share), 2)

                                # PnL multiplied by position_size
                                pnl_inr = price_move * position_size
                                pnl_pct = (price_move / entry_price) * 100 if entry_price > 0 else 0

                                await loop.run_in_executor(
                                    resolver_executor,
                                    lambda: db.resolve_prediction(
                                        pred_id=pred_id,
                                        actual_outcome=status,
                                        status=status,
                                        exit_price=current_price,
                                        holding_time_minutes=round(holding_minutes, 2),
                                        pnl_pct=round(pnl_pct, 2),
                                        pnl_inr=round(pnl_inr, 2),
                                        r_multiple=r_multiple,
                                        resolution_reason=reason,
                                    )
                                )
                                logger.info(f"[prediction_resolver] Resolved {sym}: {reason} at {current_price} (r={r_multiple}, hold={holding_minutes:.1f}m)")
                            except Exception as e:
                                logger.error(f"[prediction_resolver] Error resolving {sym} (id={pred_id}): {e}")
                        else:
                            logger.debug(f"[prediction_resolver] No hit for {sym} at {current_price}")
                    except Exception as e:
                        logger.error(f"[prediction_resolver] Error in per-prediction work for {sym} (id={pred_id}): {e}")
                        continue

                # Use dynamic poll interval
                await asyncio.sleep(poll_seconds)
            else:
                # No pending predictions: still yield, or the loop busy-spins
                # hammering get_predictions() on every tick.
                await asyncio.sleep(poll_seconds)
        except Exception as e:
            logger.error(f"[prediction_resolver] Error in resolver loop: {e}")
            await asyncio.sleep(poll_seconds)


# ── Standalone Entry Point ──────────────────────────────────────────────
# Allows running workers independently: python -m backend.trading_agent
if __name__ == "__main__":
    import sys
    import asyncio

    async def run_workers():
        """Run background workers as standalone processes."""
        logger.info("Starting standalone background workers...")
        try:
            await asyncio.gather(
                trading_agent_loop(),
                prediction_resolver_worker(),
            )
        except KeyboardInterrupt:
            logger.info("Standalone workers stopped by user")
        except Exception as e:
            logger.critical(f"Standalone worker error: {e}")
            raise

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_workers())