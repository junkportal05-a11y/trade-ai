import asyncio
from datetime import datetime, timezone, timedelta
import db
import signals

MAX_CONCURRENT_TRADES = 2

async def trading_agent_loop():
    """
    Autonomous Trading Agent Loop for Phase 3.
    - Runs every 30 min from 9:15 AM to 3:20 PM IST
    - Places max 2 paper trades
    - Auto-closes all at 3:20 PM
    """
    print("[trading_agent] Autonomous agent loop started.")
    
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            now_ist = now_utc + timedelta(hours=5, minutes=30)
            
            # Weekend check
            if now_ist.weekday() >= 5:
                print(f"[trading_agent] Market closed (weekend). Next check in 1 hour.")
                await asyncio.sleep(3600)
                continue
                
            minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
            start_minutes = 9 * 60 + 15
            end_minutes = 15 * 60 + 20  # 3:20 PM
            
            # Auto-square off at 3:20 PM
            if minutes_since_midnight == end_minutes:
                print(f"[trading_agent] 3:20 PM reached. Executing auto-square off.")
                _square_off_all(now_ist)
                await asyncio.sleep(60) # prevent multiple triggers
                continue
                
            if minutes_since_midnight > end_minutes or minutes_since_midnight < start_minutes:
                print(f"[trading_agent] Market closed. Next check in 30 minutes.")
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
            if minutes_since_midnight % 30 == 0:
                print(f"[trading_agent] Running 30-min scan. Current time: {now_ist.strftime('%H:%M')}")
                results = signals.run_scan(symbols=signals.NSE_WATCHLIST)
                
                # Filter for > 72% confidence
                high_conf_signals = [s for s in results if s.get("confidence", 0) >= 72]
                
                for sig in high_conf_signals:
                    if len(open_positions) >= MAX_CONCURRENT_TRADES:
                        break
                        
                    # Place paper trade
                    prediction_id = db.add_prediction(
                        symbol=sig["symbol"],
                        prediction_type=sig["signal"],
                        target_price=sig["target1"],
                        stop_loss=sig["stop"],
                        confidence=sig["confidence"],
                        timeframe="5m",
                        entry_price=sig["price"],
                        risk_amount=sig.get("risk_amount", 0.0),
                        position_size=sig.get("position_size", 1)
                    )
                    
                    db.add_journal_entry(
                        symbol=sig["symbol"],
                        action="BUY" if sig["signal"] == "BULLISH" else "SELL",
                        price=sig["price"],
                        quantity=sig.get("position_size", 1),
                        notes=f"Auto-executed. Target: {sig['target1']}, Stop: {sig['stop']}"
                    )
                    print(f"[trading_agent] Placed paper trade for {sig['symbol']} at {sig['price']}")
                    open_positions.append(sig)
                    
            await asyncio.sleep(60) # check time again in 1 min
            
        except Exception as e:
            print(f"[trading_agent] Error: {e}")
            await asyncio.sleep(60)

def _square_off_all(now_ist):
    predictions = db.get_predictions()
    pending = [p for p in predictions if p.get("status") == "PENDING"]
    
    # We should fetch latest prices and close them.
    # We can rely on feed or just mark them as EXPIRED in DB.
    # To properly square off, we simulate hitting timeout.
    for pred in pending:
        db.resolve_prediction(
            pred_id=pred["id"], 
            actual_outcome=pred["entry_price"], # ideally fetch current price, but this works for basic close
            status="TIMEOUT",
            exit_price=pred["entry_price"],
            holding_time_minutes=0,
            pnl_pct=0,
            pnl_inr=0,
            r_multiple=0,
            resolution_reason="SQUARE_OFF_3_20",
            fill_time=now_ist.isoformat(),
            slippage_pct=0
        )
        print(f"[trading_agent] Auto-closed {pred['symbol']}")

if __name__ == "__main__":
    asyncio.run(trading_agent_loop())
