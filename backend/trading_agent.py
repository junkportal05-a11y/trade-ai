import asyncio
from datetime import datetime, timezone, timedelta
import db
import signals
from quant.correlation_matrix import CorrelationEngine
from quant.weekly_jobs import run_weekly_maintenance
from quant.market_regime import MarketRegimeClassifier
from angelone_feed import get_angelone_feed
from trade_quality import TradeQualityEngine

MAX_CONCURRENT_TRADES = 2
MIN_AGENT_CONFIDENCE = 72

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
    
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            now_ist = now_utc + timedelta(hours=5, minutes=30)
            
            # Weekend check — run weekly maintenance on Sunday night (hour 21-22 IST)
            if now_ist.weekday() >= 5:
                if now_ist.weekday() == 6 and 21 <= now_ist.hour < 22:
                    # Sunday night: run weekly maintenance jobs
                    print(f"[trading_agent] Sunday night maintenance window. Running weekly jobs.")
                    try:
                        run_weekly_maintenance()
                    except Exception as e:
                        print(f"[trading_agent] Weekly maintenance error: {e}")
                print(f"[trading_agent] Market closed (weekend). Next check in 1 hour.")
                await asyncio.sleep(3600)
                continue
                
            minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
            start_minutes = 9 * 60 + 15
            end_minutes = 15 * 60 + 20  # 3:20 PM
            
            # Auto-square off at 3:20 PM
            if minutes_since_midnight == end_minutes:
                print("[trading_agent] 3:20 PM reached. Executing auto-square off.")
                _square_off_all(now_ist)
                await asyncio.sleep(60) # prevent multiple triggers
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
                print(f"[trading_agent] Max positions ({MAX_CONCURRENT_TRADES}) reached. Skipping scan.")
                await asyncio.sleep(1800)  # Wait 30 mins before next scan
                continue
                
            # 3. Time to scan (e.g. every 30 mins)
            current_bucket = minutes_since_midnight // 30
            if last_scan_bucket is None or current_bucket > last_scan_bucket:
                last_scan_bucket = current_bucket
                print(f"[trading_agent] Running 30-min scan. Current time: {now_ist.strftime('%H:%M')}")
                results = signals.run_scan(symbols=signals.NSE_WATCHLIST)
                
                for sig in results:
                    if sig.get("signal") not in ("BUY", "SELL"):
                        continue
                        
                    if len(open_positions) >= MAX_CONCURRENT_TRADES:
                        break
                        
<<<<<<< HEAD
                    # Place paper trade
                    pred_dict = {
                        "symbol": sig["symbol"],
                        "prediction_type": sig["signal"],
                        "target_price": sig["target1"],
                        "stop_loss": sig["stop"],
                        "confidence_score": sig["confidence"],
                        "entry_price": sig["price"],
                        "rsi": sig.get("rsi", 50),
                        "macd": sig.get("macd", 0),
                        "adx": sig.get("adx", 0),
                        "sector": sig.get("sector", "NSE"),
                        "market_cap": sig.get("market_cap", 0),
                        "volume_ratio": sig.get("volume_ratio", 1.0),
                        "vwap_distance": sig.get("vwap_distance", 0.0),
                        "risk_amount": sig.get("risk_amount", 0.0),
                        "position_size": sig.get("position_size", 1)
                    }
                    _ = db.add_prediction(pred_dict)
                    
                    journal_dict = {
                        "symbol": sig["symbol"],
                        "direction": "BUY" if sig["signal"] == "BULLISH" else "SELL",
                        "entry_price": sig["price"],
                        "exit_price": 0.0,
                        "qty": sig.get("position_size", 1),
                        "entry_date": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
                        "reason": f"Auto-executed. Target: {sig['target1']}, Stop: {sig['stop']}",
                        "emotion": "Neutral",
                        "status": "OPEN",
                        "pnl": 0.0
                    }
                    db.add_journal_entry(journal_dict)
=======
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
>>>>>>> c3fffc7 (feat: complete Phase 1 - Market Regime Classifier and Operational Hygiene)
                    print(f"[trading_agent] Placed paper trade for {sig['symbol']} at {sig['price']}")
                    open_positions.append({"id": prediction_id, **sig})
                    
            await asyncio.sleep(60) # check time again in 1 min
            
        except Exception as e:
            print(f"[trading_agent] Error: {e}")
            await asyncio.sleep(60)

def _square_off_all(now_ist):
    predictions = db.get_predictions()
    pending = [p for p in predictions if p.get("status") == "PENDING"]
    
    feed = get_angelone_feed()
    
    for pred in pending:
        # Fetch live quote for square off
        quotes = feed.get_live_quotes([pred["symbol"]]) if feed.is_authorized() else {}
        live_quote = quotes.get(pred["symbol"])
        if live_quote and "price" in live_quote:
            exit_price = float(live_quote["price"])
        else:
            exit_price = float(pred["entry_price"]) # Fallback
            
        entry_price = float(pred["entry_price"])
        
        if pred["prediction_type"] in ["BUY", "BULLISH"]:
            pnl_inr = (exit_price - entry_price) * pred.get("position_size", 1)
        else:
            pnl_inr = (entry_price - exit_price) * pred.get("position_size", 1)
            
        pnl_pct = (pnl_inr / (entry_price * pred.get("position_size", 1))) * 100 if entry_price > 0 else 0
        
        db.resolve_prediction(
            pred_id=pred["id"], 
            actual_outcome=exit_price,
            status="TIMEOUT",
            exit_price=exit_price,
            holding_time_minutes=0,
            pnl_pct=round(pnl_pct, 2),
            pnl_inr=round(pnl_inr, 2),
            r_multiple=0,
            resolution_reason="SQUARE_OFF_3_20",
            fill_time=now_ist.isoformat(),
            slippage_pct=0
        )
        print(f"[trading_agent] Auto-closed {pred['symbol']} at {exit_price}")


def _build_prediction_payload(sig: dict) -> dict:
    direction = sig.get("signal") or sig.get("direction") or "BUY"
    entry_price = float(sig.get("price") or sig.get("entry") or sig.get("entry_price") or 0.0)
    target_price = float(sig.get("target1") or sig.get("target") or sig.get("target_price") or entry_price)
    stop_loss = float(sig.get("stop_loss") or sig.get("stop") or entry_price)
    vwap = float(sig.get("vwap") or entry_price or 1.0)
    vwap_distance = ((entry_price - vwap) / vwap * 100) if vwap else 0.0

    return {
        "symbol": sig["symbol"],
        "prediction_type": direction,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
        "confidence_score": int(sig.get("confidence", 0)),
        "rsi": float(sig.get("rsi", 50.0)),
        "macd": float(sig.get("macd_hist", 0.0)),
        "adx": float(sig.get("adx", 0.0)),
        "sector": sig.get("sector", "NSE"),
        "market_cap": float(sig.get("market_cap", 0.0)),
        "volume_ratio": float(sig.get("vol_ratio", sig.get("volume_ratio", 0.0))),
        "vwap_distance": vwap_distance,
        "atr": float(sig.get("atr", 0.0)),
        "news_score": float(sig.get("news_sentiment", sig.get("news_score", 0.0))),
        "market_breadth": float(sig.get("market_breadth", 0.0)),
        "sector_strength": float(sig.get("sector_score", 0.0)),
        "nifty_trend": sig.get("nifty_trend", "FLAT"),
        "status": "PENDING",
        "reason": sig.get("reasoning") or ", ".join(sig.get("reasons", [])),
        "setup_type": sig.get("setup_type", "SYSTEM_EDGE"),
        "market_regime_snapshot": sig.get("market_regime", sig.get("market_regime_snapshot", "UNKNOWN")),
        "risk_amount": float(sig.get("risk_amount", 0.0)),
        "confidence_probability": float(sig.get("confidence_probability", 0.0)),
        "regime_score": float(sig.get("regime_score", 0.0)),
        "volume_score": float(sig.get("volume_score", 0.0)),
        "rs_score": float(sig.get("rs_score", 0.0)),
        "trade_quality_score": float(sig.get("trade_quality_score", 0.0)),
        "correlation_score": float(sig.get("correlation_score", 0.0)),
    }


def _build_journal_payload(sig: dict) -> dict:
    direction = sig.get("signal") or sig.get("direction") or "BUY"
    entry_price = float(sig.get("price") or sig.get("entry") or sig.get("entry_price") or 0.0)
    quantity = int(float(sig.get("quantity") or sig.get("position_size") or 1))
    target = sig.get("target1") or sig.get("target") or sig.get("target_price")
    stop = sig.get("stop_loss") or sig.get("stop")

    return {
        "symbol": sig["symbol"],
        "direction": direction,
        "entry_price": entry_price,
        "qty": max(1, quantity),
        "reason": f"Auto-executed. Target: {target}, Stop: {stop}",
        "emotion": "Systematic",
        "status": "OPEN",
    }


if __name__ == "__main__":
    asyncio.run(trading_agent_loop())
