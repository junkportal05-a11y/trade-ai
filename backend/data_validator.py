import pandas as pd
import numpy as np
from datetime import timedelta

def calculate_confidence(df: pd.DataFrame, interval: str = "5m") -> float:
    """
    Calculates the Data Confidence Score (0-100) for a given OHLCV DataFrame.
    Penalizes for:
      - Missing bars (time gaps)
      - Zero volume bars (stale ticks / no liquidity)
      - Flatlines (Open == High == Low == Close)
    """
    if df is None or df.empty or len(df) < 5:
        return 0.0

    score = 100.0
    
    # Check for flatlines
    flatlines = df[(df['Open'] == df['High']) & (df['High'] == df['Low']) & (df['Low'] == df['Close'])]
    flatline_pct = len(flatlines) / len(df)
    score -= (flatline_pct * 100)  # Heavy penalty for flatlines

    # Check for zero volume
    if 'Volume' in df.columns:
        zero_vol = df[df['Volume'] <= 0]
        zero_vol_pct = len(zero_vol) / len(df)
        score -= (zero_vol_pct * 100)  # Heavy penalty for zero volume
        
    # Check for time gaps if index is datetime
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        # Calculate expected timedelta based on interval
        # Basic mapping for typical intervals
        expected_td = timedelta(minutes=5)
        if interval == "1m": expected_td = timedelta(minutes=1)
        elif interval == "15m": expected_td = timedelta(minutes=15)
        elif interval == "1d": expected_td = timedelta(days=1)
        
        diffs = df.index.to_series().diff().dropna()
        # Count gaps that are strictly greater than expected_td (allow some tolerance for weekends if daily)
        if interval in ["1m", "5m", "15m"]:
            # Intraday: Any gap > expected is a hole (ignoring overnight gaps which are typical, 
            # so we only penalize gaps within the same trading day)
            same_day_diffs = diffs[df.index[1:].date == df.index[:-1].date]
            gaps = same_day_diffs[same_day_diffs > expected_td]
            
            # Penalize 2 points for every missing intraday bar equivalent
            for gap in gaps:
                missing_bars = (gap.total_seconds() / expected_td.total_seconds()) - 1
                if missing_bars > 0:
                    score -= (missing_bars * 2)

    return max(0.0, min(100.0, score))

import psycopg2
import os
import json
from dotenv import load_dotenv

def get_db_connection():
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=False)
    load_dotenv(override=False)
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set.")
    return psycopg2.connect(DATABASE_URL)

def validate_trade(trade: dict) -> dict:
    failures = []
    warnings = []
    
    entry_price = trade.get('entry_price')
    target = trade.get('target_price') or trade.get('target')
    stop_loss = trade.get('stop_loss')
    direction = trade.get('prediction_type') or trade.get('signal_type')
    
    if entry_price is None:
        failures.append("entry_price is null")
    elif entry_price <= 0:
        failures.append("entry_price <= 0")
        
    if stop_loss is not None and entry_price is not None and direction:
        if direction in ['BUY', 'BULLISH']:
            if stop_loss >= entry_price:
                failures.append("stop_loss >= entry_price (BUY)")
            if target is not None and target <= entry_price:
                failures.append("target <= entry_price (BUY)")
        elif direction in ['SELL', 'BEARISH']:
            if stop_loss <= entry_price:
                failures.append("stop_loss <= entry_price (SELL)")
            if target is not None and target >= entry_price:
                failures.append("target >= entry_price (SELL)")
                
    resolved_at = trade.get('resolved_at')
    created_at = trade.get('prediction_date') or trade.get('created_at')
    if resolved_at and created_at:
        if str(resolved_at) <= str(created_at):
            failures.append("resolved_at <= created_at")
            
    status = trade.get('status')
    if status not in ['WIN', 'LOSS', 'TIMEOUT', 'OPEN', 'PENDING']:
        failures.append("result is not one of WIN/LOSS/TIMEOUT/OPEN/PENDING")
        
    if status in ['WIN', 'LOSS']:
        exit_price = trade.get('exit_price')
        pnl_inr = trade.get('pnl_inr') or trade.get('pnl') or 0.0
        
        if exit_price is None or exit_price <= 0:
            failures.append("exit_price missing or <= 0 for resolved trade")
            
        if status == 'WIN' and pnl_inr <= 0:
            failures.append("WIN status but PnL <= 0")
        if status == 'LOSS' and pnl_inr >= 0:
            failures.append("LOSS status but PnL >= 0")
        
    regime = trade.get('market_regime_snapshot')
    if not regime or regime == 'UNKNOWN' or regime == 'UNCLEAR':
        failures.append("regime is null or UNCLEAR")
        
    score = 100 if len(failures) == 0 else max(0, 100 - (len(failures) * 20))
    
    return {
        "valid": len(failures) == 0,
        "score": score,
        "failures": failures,
        "warnings": warnings
    }

def calculate_confidence_from_counts(valid: int, total: int) -> float:
    """
    Pure math function for computing data confidence.
    Handles zero-trades edge case.
    """
    if total <= 0:
        return 0.0
    return (valid / total) * 100.0

def calculate_data_confidence(limit: int = 100, persist: bool = True) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM predictions_history WHERE status IN ('WIN', 'LOSS', 'TIMEOUT') ORDER BY id DESC LIMIT %s;", (limit,))
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        if not rows:
            return {"confidence_score": 100.0, "locked": False, "failures": []}
            
        total_trades = len(rows)
        valid_trades = 0
        all_failures = []
        
        for row in rows:
            trade_dict = dict(zip(columns, row))
            validation = validate_trade(trade_dict)
            if validation["valid"]:
                valid_trades += 1
            else:
                all_failures.extend(validation["failures"])
                
        confidence_score = calculate_confidence_from_counts(valid_trades, total_trades)
        locked = confidence_score < 90.0
        
        if persist:
            cur.execute(
                """
                INSERT INTO data_quality (total_trades, valid_trades, confidence_score, failures, locked)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (total_trades, valid_trades, confidence_score, json.dumps(list(set(all_failures))), locked)
            )
            conn.commit()
            
        return {
            "confidence_score": confidence_score,
            "locked": locked,
            "failures": list(set(all_failures))
        }
    finally:
        cur.close()
        conn.close()

