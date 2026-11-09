import pandas as pd
import numpy as np
import time

def test_perf():
    np.random.seed(42)
    N = 100000
    df = pd.DataFrame({
        'Close': np.random.randn(N).cumsum(),
        'Volume': np.random.randint(1, 100, N)
    })
    close = df['Close']
    volume = df['Volume']

    # Slow implementation
    t0 = time.time()
    obv = [0]
    for i in range(1, len(df)):
        if close.iloc[i] > close.iloc[i - 1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i - 1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    df["OBV_slow"] = obv
    t1 = time.time()
    slow_time = t1 - t0

    # Fast implementation
    t2 = time.time()
    df["OBV_fast"] = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0)).cumsum()
    t3 = time.time()
    fast_time = t3 - t2

    # Check correctness
    pd.testing.assert_series_equal(df["OBV_slow"], df["OBV_fast"], check_names=False)
    print(f"Slow time: {slow_time:.5f}s")
    print(f"Fast time: {fast_time:.5f}s")
    print(f"Improvement: {slow_time/fast_time:.2f}x")


def test_supertrend_perf():
    from signals import _supertrend, _atr

    np.random.seed(42)
    N = 1000
    high = pd.Series(np.random.rand(N) + 100)
    low = pd.Series(high - np.random.rand(N))
    close = pd.Series((high + low) / 2)

    # Slow implementation using .iloc on pandas Series
    t0 = time.time()
    _, tr = _atr(high, low, close, 7)
    atr_s = tr.rolling(7).mean()
    basic_upper = (high + low) / 2 + 3.0 * atr_s
    basic_lower = (high + low) / 2 - 3.0 * atr_s
    supert_slow = pd.Series(np.nan, index=close.index)
    supert_dir_slow = pd.Series(1.0, index=close.index)
    for i in range(1, len(close)):
        bu = basic_upper.iloc[i]
        bl = basic_lower.iloc[i]
        prev = supert_slow.iloc[i - 1] if not np.isnan(supert_slow.iloc[i - 1]) else bl
        pd_ = supert_dir_slow.iloc[i - 1]
        bl = max(bl, prev) if pd_ == 1 else bl
        bu = min(bu, prev) if pd_ == -1 else bu
        if close.iloc[i - 1] <= prev:
            supert_slow.iloc[i] = bu
            supert_dir_slow.iloc[i] = -1
        else:
            supert_slow.iloc[i] = bl
            supert_dir_slow.iloc[i] = 1
    t1 = time.time()
    slow_time = t1 - t0

    # Optimized implementation using NumPy 1D arrays
    t2 = time.time()
    supert_fast, supert_dir_fast = _supertrend(high, low, close, period=7, multiplier=3.0)
    t3 = time.time()
    fast_time = t3 - t2

    # Verify identical output
    pd.testing.assert_series_equal(supert_slow, supert_fast, check_names=False)
    pd.testing.assert_series_equal(supert_dir_slow, supert_dir_fast, check_names=False)
    print(f"Supertrend Slow (.iloc): {slow_time:.5f}s, Fast (NumPy): {fast_time:.5f}s, Speedup: {slow_time/fast_time:.1f}x")
    assert fast_time < slow_time, "NumPy implementation should be faster than pandas .iloc"


def test_backtest_engine_perf():
    import math
    from backend.backtest_engine import (
        BacktestConfig,
        _compute_indicators,
        _calculate_daily_score,
        resolve_candle_pessimistic,
    )

    rng = np.random.default_rng(42)
    N = 1000
    idx = pd.date_range("2020-01-01", periods=N, freq="D")
    close = 100 + np.cumsum(rng.normal(0, 1, N))
    high = close + rng.uniform(0, 2, N)
    low = close - rng.uniform(0, 2, N)
    open_ = close + rng.normal(0, 0.5, N)
    volume = rng.integers(1_000, 5_000, N)
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )
    df = _compute_indicators(df)
    config = BacktestConfig()

    # Baseline slow implementation (.iloc inside simulation loop)
    t0 = time.time()
    capital_slow = config.initial_capital
    position_slow = None
    trades_slow = []
    close_s = df["Close"]
    high_s = df["High"]
    low_s = df["Low"]
    open_s = df["Open"]

    for i in range(25, len(df)):
        current_date = df.index[i].strftime("%Y-%m-%d")
        price = float(close_s.iloc[i])
        curr_high = float(high_s.iloc[i])
        curr_low = float(low_s.iloc[i])
        atr_val = df["ATR"].iloc[i]

        if position_slow:
            candle = {"high": curr_high, "low": curr_low, "open": float(open_s.iloc[i])}
            result, exit_p = resolve_candle_pessimistic(
                candle,
                entry=position_slow["entry_price"],
                target=position_slow["target"],
                stop=position_slow["stop_loss"],
                direction="BUY",
            )
            if result == "LOSS" or result == "WIN":
                pnl = (exit_p - position_slow["entry_price"]) * position_slow["shares"]
                capital_slow += position_slow["shares"] * exit_p
                trades_slow.append({"pnl": round(pnl, 2), "status": result})
                position_slow = None
                continue

        score = _calculate_daily_score(df, i)
        if position_slow and score <= config.early_exit:
            pnl = (price - position_slow["entry_price"]) * position_slow["shares"]
            capital_slow += position_slow["shares"] * price
            trades_slow.append({"pnl": round(pnl, 2), "status": "CLOSED"})
            position_slow = None
            continue

        if not position_slow and score >= config.entry_score:
            if np.isnan(atr_val) or np.isnan(price):
                continue
            stop_loss = round(price - config.stop_atr * atr_val, 2)
            target = round(price + config.target_atr * atr_val, 2)
            if np.isnan(stop_loss) or np.isnan(target):
                continue
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            max_risk_money = capital_slow * config.risk_pct
            shares_by_risk = math.floor(max_risk_money / risk_per_share)
            shares_by_cap = math.floor((capital_slow * 0.95) / price)
            shares = min(shares_by_risk, shares_by_cap)
            if shares >= 1:
                actual_cost = round(shares * price, 2)
                capital_slow -= actual_cost
                position_slow = {
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "shares": shares,
                    "entry_date": current_date,
                }
    t1 = time.time()
    slow_time = t1 - t0

    # Fast NumPy implementation (as optimized in backtest_engine.py)
    t2 = time.time()
    capital_fast = config.initial_capital
    position_fast = None
    trades_fast = []

    close_np = df["Close"].to_numpy()
    high_np = df["High"].to_numpy()
    low_np = df["Low"].to_numpy()
    open_np = df["Open"].to_numpy()
    atr_np = df["ATR"].to_numpy()
    dates = df.index.strftime("%Y-%m-%d")

    adx_np = df["ADX"].to_numpy()
    rsi_np = df["RSI"].to_numpy()
    sma50_np = df["SMA50"].to_numpy()
    valid_score_mask = ~(np.isnan(adx_np) | np.isnan(rsi_np) | np.isnan(sma50_np))
    scores = np.zeros(len(df), dtype=int)
    scores += np.where(valid_score_mask & (adx_np > 20), 3, 0)
    scores += np.where(
        valid_score_mask & (rsi_np < 35),
        3,
        np.where(valid_score_mask & (rsi_np > 70), -5, 0),
    )
    scores += np.where(valid_score_mask & (close_np > sma50_np), 2, 0)

    for i in range(25, len(df)):
        current_date = dates[i]
        price = float(close_np[i])
        curr_high = float(high_np[i])
        curr_low = float(low_np[i])
        atr_val = atr_np[i]

        if position_fast:
            candle = {"high": curr_high, "low": curr_low, "open": float(open_np[i])}
            result, exit_p = resolve_candle_pessimistic(
                candle,
                entry=position_fast["entry_price"],
                target=position_fast["target"],
                stop=position_fast["stop_loss"],
                direction="BUY",
            )
            if result == "LOSS" or result == "WIN":
                pnl = (exit_p - position_fast["entry_price"]) * position_fast["shares"]
                capital_fast += position_fast["shares"] * exit_p
                trades_fast.append({"pnl": round(pnl, 2), "status": result})
                position_fast = None
                continue

        score = int(scores[i])
        if position_fast and score <= config.early_exit:
            pnl = (price - position_fast["entry_price"]) * position_fast["shares"]
            capital_fast += position_fast["shares"] * price
            trades_fast.append({"pnl": round(pnl, 2), "status": "CLOSED"})
            position_fast = None
            continue

        if not position_fast and score >= config.entry_score:
            if np.isnan(atr_val) or np.isnan(price):
                continue
            stop_loss = round(price - config.stop_atr * atr_val, 2)
            target = round(price + config.target_atr * atr_val, 2)
            if np.isnan(stop_loss) or np.isnan(target):
                continue
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            max_risk_money = capital_fast * config.risk_pct
            shares_by_risk = math.floor(max_risk_money / risk_per_share)
            shares_by_cap = math.floor((capital_fast * 0.95) / price)
            shares = min(shares_by_risk, shares_by_cap)
            if shares >= 1:
                actual_cost = round(shares * price, 2)
                capital_fast -= actual_cost
                position_fast = {
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "shares": shares,
                    "entry_date": current_date,
                }
    t3 = time.time()
    fast_time = t3 - t2

    assert round(capital_slow, 2) == round(capital_fast, 2)
    assert len(trades_slow) == len(trades_fast)
    print(
        f"Backtest Engine Slow (.iloc): {slow_time:.5f}s, Fast (NumPy): {fast_time:.5f}s, Speedup: {slow_time/fast_time:.1f}x"
    )
    assert fast_time < slow_time, "NumPy implementation should be faster than pandas .iloc"


if __name__ == "__main__":
    test_perf()
    test_supertrend_perf()
    test_backtest_engine_perf()
