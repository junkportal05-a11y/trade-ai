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
            same_day_diffs = diffs[diffs.index.date == diffs.index.to_series().shift(1).dt.date.dropna()]
            gaps = same_day_diffs[same_day_diffs > expected_td]
            
            # Penalize 2 points for every missing intraday bar equivalent
            for gap in gaps:
                missing_bars = (gap.total_seconds() / expected_td.total_seconds()) - 1
                if missing_bars > 0:
                    score -= (missing_bars * 2)

    return max(0.0, min(100.0, score))
