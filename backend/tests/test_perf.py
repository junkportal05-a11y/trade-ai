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


def test_backtest_loop_perf():
    import backtest_engine as bt

    np.random.seed(42)
    N = 1000
    dates = pd.date_range("2020-01-01", periods=N, freq="D")
    df = pd.DataFrame(
        {
            "Open": 100 + np.random.randn(N).cumsum(),
            "High": 105 + np.random.randn(N).cumsum(),
            "Low": 95 + np.random.randn(N).cumsum(),
            "Close": 100 + np.random.randn(N).cumsum(),
            "Volume": np.random.randint(1000, 10000, size=N),
        },
        index=dates,
    )
    df["High"] = df[["Open", "Close", "High"]].max(axis=1) + 1.0
    df["Low"] = df[["Open", "Close", "Low"]].min(axis=1) - 1.0

    df_ind = bt._compute_indicators(df)
    cfg = bt.BacktestConfig()

    # Baseline slow implementation (.iloc inside loop)
    t0 = time.perf_counter()
    capital_slow = cfg.initial_capital
    pos_slow = None
    trades_slow = []
    close_s = df_ind["Close"]
    high_s = df_ind["High"]
    low_s = df_ind["Low"]
    open_s = df_ind["Open"]
    for i in range(25, len(df_ind)):
        price = float(close_s.iloc[i])
        curr_high = float(high_s.iloc[i])
        curr_low = float(low_s.iloc[i])
        atr_val = df_ind["ATR"].iloc[i]
        if pos_slow:
            candle = {"high": curr_high, "low": curr_low, "open": float(open_s.iloc[i])}
            result, exit_p = bt.resolve_candle_pessimistic(
                candle, pos_slow["entry_price"], pos_slow["target"], pos_slow["stop_loss"], "BUY"
            )
            if result in ("LOSS", "WIN"):
                capital_slow += pos_slow["shares"] * exit_p
                trades_slow.append((i, result, exit_p))
                pos_slow = None
                continue
        score = bt._calculate_daily_score(df_ind, i)
        if pos_slow and score <= cfg.early_exit:
            capital_slow += pos_slow["shares"] * price
            trades_slow.append((i, "EARLY_EXIT", price))
            pos_slow = None
            continue
        if not pos_slow and score >= cfg.entry_score:
            if np.isnan(atr_val) or np.isnan(price):
                continue
            stop_loss = round(price - cfg.stop_atr * atr_val, 2)
            target = round(price + cfg.target_atr * atr_val, 2)
            if np.isnan(stop_loss) or np.isnan(target):
                continue
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            shares = min(
                int((capital_slow * cfg.risk_pct) / risk_per_share),
                int((capital_slow * 0.95) / price),
            )
            if shares >= 1:
                capital_slow -= round(shares * price, 2)
                pos_slow = {
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "shares": shares,
                }
    t1 = time.perf_counter()
    slow_time = t1 - t0

    # Optimized implementation (NumPy 1D arrays + _calculate_daily_score_fast)
    t2 = time.perf_counter()
    close_arr = df_ind["Close"].to_numpy(dtype=float)
    high_arr = df_ind["High"].to_numpy(dtype=float)
    low_arr = df_ind["Low"].to_numpy(dtype=float)
    open_arr = df_ind["Open"].to_numpy(dtype=float)
    atr_arr = df_ind["ATR"].to_numpy(dtype=float)
    adx_arr = df_ind["ADX"].to_numpy(dtype=float)
    rsi_arr = df_ind["RSI"].to_numpy(dtype=float)
    sma50_arr = df_ind["SMA50"].to_numpy(dtype=float)

    capital_fast = cfg.initial_capital
    pos_fast = None
    trades_fast = []
    for i in range(25, len(df_ind)):
        price = close_arr[i]
        curr_high = high_arr[i]
        curr_low = low_arr[i]
        atr_val = atr_arr[i]
        if pos_fast:
            candle = {"high": curr_high, "low": curr_low, "open": open_arr[i]}
            result, exit_p = bt.resolve_candle_pessimistic(
                candle, pos_fast["entry_price"], pos_fast["target"], pos_fast["stop_loss"], "BUY"
            )
            if result in ("LOSS", "WIN"):
                capital_fast += pos_fast["shares"] * exit_p
                trades_fast.append((i, result, exit_p))
                pos_fast = None
                continue
        score = bt._calculate_daily_score_fast(adx_arr[i], rsi_arr[i], price, sma50_arr[i])
        if pos_fast and score <= cfg.early_exit:
            capital_fast += pos_fast["shares"] * price
            trades_fast.append((i, "EARLY_EXIT", price))
            pos_fast = None
            continue
        if not pos_fast and score >= cfg.entry_score:
            if np.isnan(atr_val) or np.isnan(price):
                continue
            stop_loss = round(price - cfg.stop_atr * atr_val, 2)
            target = round(price + cfg.target_atr * atr_val, 2)
            if np.isnan(stop_loss) or np.isnan(target):
                continue
            risk_per_share = price - stop_loss
            if risk_per_share <= 0:
                continue
            shares = min(
                int((capital_fast * cfg.risk_pct) / risk_per_share),
                int((capital_fast * 0.95) / price),
            )
            if shares >= 1:
                capital_fast -= round(shares * price, 2)
                pos_fast = {
                    "entry_price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "shares": shares,
                }
    t3 = time.perf_counter()
    fast_time = t3 - t2

    # Verify 100% parity
    assert capital_slow == capital_fast, f"Capital mismatch: {capital_slow} vs {capital_fast}"
    assert trades_slow == trades_fast, f"Trades mismatch: {len(trades_slow)} vs {len(trades_fast)}"
    print(f"Backtest Loop Slow (.iloc): {slow_time:.5f}s, Fast (NumPy): {fast_time:.5f}s, Speedup: {slow_time/fast_time:.1f}x")
    assert fast_time < slow_time, "Fast NumPy simulation should be faster than pandas .iloc loop"


if __name__ == "__main__":
    test_perf()
    test_supertrend_perf()
    test_backtest_loop_perf()
