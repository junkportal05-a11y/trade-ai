import pandas as pd
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
    flatlines = df[
        (df["Open"] == df["High"])
        & (df["High"] == df["Low"])
        & (df["Low"] == df["Close"])
    ]
    flatline_pct = len(flatlines) / len(df)
    score -= flatline_pct * 100  # Heavy penalty for flatlines

    # Check for zero volume
    if "Volume" in df.columns:
        zero_vol = df[df["Volume"] <= 0]
        zero_vol_pct = len(zero_vol) / len(df)
        score -= zero_vol_pct * 100  # Heavy penalty for zero volume

    # Check for time gaps if index is datetime
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        # Calculate expected timedelta based on interval
        # Basic mapping for typical intervals
        expected_td = timedelta(minutes=5)
        if interval == "1m":
            expected_td = timedelta(minutes=1)
        elif interval == "15m":
            expected_td = timedelta(minutes=15)
        elif interval == "1d":
            expected_td = timedelta(days=1)

        diffs = df.index.to_series().diff().dropna()
        # Count gaps that are strictly greater than expected_td (allow some tolerance for weekends if daily)
        if interval in ["1m", "5m", "15m"]:
            # Intraday: Any gap > expected is a hole (ignoring overnight gaps which are typical,
            # so we only penalize gaps within the same trading day)
            same_day_diffs = diffs[
                diffs.index.date == diffs.index.to_series().shift(1).dt.date.dropna()
            ]
            gaps = same_day_diffs[same_day_diffs > expected_td]

            # Penalize 2 points for every missing intraday bar equivalent
            for gap in gaps:
                missing_bars = (gap.total_seconds() / expected_td.total_seconds()) - 1
                if missing_bars > 0:
                    score -= missing_bars * 2

    return max(0.0, min(100.0, score))


def validate_trade(trade: dict) -> dict:
    failures = []
    warnings = []

    entry_price = trade.get("entry_price")
    target = trade.get("target_price") or trade.get("target")
    stop_loss = trade.get("stop_loss")
    direction = trade.get("prediction_type") or trade.get("signal_type")

    if entry_price is None:
        failures.append("entry_price is null")
    elif entry_price <= 0:
        failures.append("entry_price <= 0")

    if stop_loss is not None and entry_price is not None and direction:
        if direction in ["BUY", "BULLISH"]:
            if stop_loss >= entry_price:
                failures.append("stop_loss >= entry_price (BUY)")
            if target is not None and target <= entry_price:
                failures.append("target <= entry_price (BUY)")
        elif direction in ["SELL", "BEARISH"]:
            if stop_loss <= entry_price:
                failures.append("stop_loss <= entry_price (SELL)")
            if target is not None and target >= entry_price:
                failures.append("target >= entry_price (SELL)")

    resolved_at = trade.get("resolved_at")
    created_at = trade.get("prediction_date") or trade.get("created_at")
    if resolved_at and created_at:
        if str(resolved_at) <= str(created_at):
            failures.append("resolved_at <= created_at")

    status = trade.get("status")
    if status not in ["WIN", "LOSS", "TIMEOUT", "OPEN", "PENDING"]:
        failures.append("result is not one of WIN/LOSS/TIMEOUT/OPEN/PENDING")

    if status in ["WIN", "LOSS"]:
        exit_price = trade.get("exit_price")
        pnl_inr = trade.get("pnl_inr") or trade.get("pnl") or 0.0

        if exit_price is None or exit_price <= 0:
            failures.append("exit_price missing or <= 0 for resolved trade")

        if status == "WIN" and pnl_inr <= 0:
            failures.append("WIN status but PnL <= 0")
        if status == "LOSS" and pnl_inr >= 0:
            failures.append("LOSS status but PnL >= 0")

    regime = trade.get("market_regime_snapshot")
    if not regime or regime == "UNKNOWN" or regime == "UNCLEAR":
        failures.append("regime is null or UNCLEAR")

    score = 100 if len(failures) == 0 else max(0, 100 - (len(failures) * 20))

    return {
        "valid": len(failures) == 0,
        "score": score,
        "failures": failures,
        "warnings": warnings,
    }


def calculate_confidence_from_counts(valid: int, total: int) -> float:
    """
    Pure math function for computing data confidence.
    Handles zero-trades edge case.
    """
    if total <= 0:
        return 0.0
    return (valid / total) * 100.0
