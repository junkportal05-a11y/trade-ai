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
    from backtest_engine import BacktestConfig, resolve_candle_pessimistic, _calculate_daily_score, _calculate_daily_scores

    np.random.seed(42)
    N = 2500  # ~10 years of trading days
    dates = pd.date_range("2015-01-01", periods=N, freq="B")
    close = 100.0 + np.random.randn(N).cumsum()
    high = close + np.random.uniform(0.5, 2.0, N)
    low = close - np.random.uniform(0.5, 2.0, N)
    open_p = close + np.random.uniform(-0.5, 0.5, N)
    atr = np.random.uniform(1.0, 3.0, N)
    adx = np.random.uniform(10, 40, N)
    rsi = np.random.uniform(20, 80, N)
    sma50 = close - np.random.uniform(-2, 2, N)

    df = pd.DataFrame({
        "Open": open_p, "High": high, "Low": low, "Close": close,
        "ATR": atr, "ADX": adx, "RSI": rsi, "SMA50": sma50
    }, index=dates)

    config = BacktestConfig()

    # 1. Baseline unoptimized implementation using Series .iloc inside the loop
    t0 = time.time()
    capital_1 = 100000.0
    position_1 = None
    trades_1 = []
    equity_1 = []
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

        pos_value = 0
        if position_1:
            pos_value = position_1["shares"] * price
        equity_1.append({"date": current_date, "value": round(capital_1 + pos_value, 2)})

        if position_1:
            candle = {"high": curr_high, "low": curr_low, "open": float(open_s.iloc[i])}
            result, exit_p = resolve_candle_pessimistic(
                candle,
                entry=position_1["entry_price"],
                target=position_1["target"],
                stop=position_1["stop_loss"],
                direction="BUY"
            )
            if result in ("LOSS", "WIN"):
                pnl = (exit_p - position_1["entry_price"]) * position_1["shares"]
                capital_1 += position_1["shares"] * exit_p
                trades_1.append({"exit_p": exit_p, "pnl": pnl})
                position_1 = None
                continue

        score = _calculate_daily_score(df, i)
        if position_1 and score <= config.early_exit:
            pnl = (price - position_1["entry_price"]) * position_1["shares"]
            capital_1 += position_1["shares"] * price
            trades_1.append({"exit_p": price, "pnl": pnl})
            position_1 = None
            continue

        if not position_1 and score >= config.entry_score:
            if np.isnan(atr_val) or np.isnan(price):
                continue
            stop_loss = round(price - config.stop_atr * atr_val, 2)
            target = round(price + config.target_atr * atr_val, 2)
            if np.isnan(stop_loss) or np.isnan(target):
                continue
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            max_risk_money = capital_1 * config.risk_pct
            shares_by_risk = math.floor(max_risk_money / risk_per_share)
            shares_by_cap = math.floor((capital_1 * 0.95) / price)
            shares = min(shares_by_risk, shares_by_cap)
            if shares >= 1:
                actual_cost = round(shares * price, 2)
                capital_1 -= actual_cost
                position_1 = {
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "shares": shares,
                    "entry_date": current_date,
                }
    t1 = time.time()
    slow_time = t1 - t0

    # 2. Optimized implementation with pre-extracted NumPy buffers and vectorized scoring
    t2 = time.time()
    capital_2 = 100000.0
    position_2 = None
    trades_2 = []
    equity_2 = []

    close_np = df["Close"].to_numpy(dtype=float, copy=False)
    high_np = df["High"].to_numpy(dtype=float, copy=False)
    low_np = df["Low"].to_numpy(dtype=float, copy=False)
    open_np = df["Open"].to_numpy(dtype=float, copy=False)
    atr_np = df["ATR"].to_numpy(dtype=float, copy=False)
    date_strings = df.index.strftime("%Y-%m-%d")
    daily_scores = _calculate_daily_scores(df)

    for i in range(25, len(df)):
        current_date = date_strings[i]
        price = float(close_np[i])
        curr_high = float(high_np[i])
        curr_low = float(low_np[i])
        atr_val = atr_np[i]

        pos_value = 0
        if position_2:
            pos_value = position_2["shares"] * price
        equity_2.append({"date": current_date, "value": round(capital_2 + pos_value, 2)})

        if position_2:
            candle = {"high": curr_high, "low": curr_low, "open": float(open_np[i])}
            result, exit_p = resolve_candle_pessimistic(
                candle,
                entry=position_2["entry_price"],
                target=position_2["target"],
                stop=position_2["stop_loss"],
                direction="BUY"
            )
            if result in ("LOSS", "WIN"):
                pnl = (exit_p - position_2["entry_price"]) * position_2["shares"]
                capital_2 += position_2["shares"] * exit_p
                trades_2.append({"exit_p": exit_p, "pnl": pnl})
                position_2 = None
                continue

        score = int(daily_scores[i])
        if position_2 and score <= config.early_exit:
            pnl = (price - position_2["entry_price"]) * position_2["shares"]
            capital_2 += position_2["shares"] * price
            trades_2.append({"exit_p": price, "pnl": pnl})
            position_2 = None
            continue

        if not position_2 and score >= config.entry_score:
            if np.isnan(atr_val) or np.isnan(price):
                continue
            stop_loss = round(price - config.stop_atr * atr_val, 2)
            target = round(price + config.target_atr * atr_val, 2)
            if np.isnan(stop_loss) or np.isnan(target):
                continue
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            max_risk_money = capital_2 * config.risk_pct
            shares_by_risk = math.floor(max_risk_money / risk_per_share)
            shares_by_cap = math.floor((capital_2 * 0.95) / price)
            shares = min(shares_by_risk, shares_by_cap)
            if shares >= 1:
                actual_cost = round(shares * price, 2)
                capital_2 -= actual_cost
                position_2 = {
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "shares": shares,
                    "entry_date": current_date,
                }
    t3 = time.time()
    fast_time = t3 - t2

    # Assert exact trade and equity parity
    assert trades_1 == trades_2, "Trades must match identically"
    assert equity_1 == equity_2, "Equity curves must match identically"
    assert round(capital_1, 2) == round(capital_2, 2), "Final capital must match"

    speedup = slow_time / fast_time
    print(f"Backtest Engine Loop Slow (.iloc): {slow_time:.5f}s, Fast (NumPy buffers): {fast_time:.5f}s, Speedup: {speedup:.1f}x")
    assert speedup > 2.0, f"Expected >2x speedup under test load, got {speedup:.1f}x"
    assert fast_time < slow_time, "Optimized NumPy implementation must be faster than Series .iloc"


if __name__ == "__main__":
    test_perf()
    test_supertrend_perf()
    test_backtest_engine_perf()
