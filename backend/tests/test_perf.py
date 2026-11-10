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


def test_kama_perf():
    from strategy_tournament import _compute_indicators

    np.random.seed(42)
    N = 2000
    close = pd.Series(np.random.randn(N).cumsum() + 100)
    change = (close - close.shift(10)).abs()
    volatility = close.diff().abs().rolling(10).sum()
    er = change / (volatility + 1e-9)
    sc = (er * (2 / 3 - 2 / 31) + 2 / 31) ** 2

    # Slow implementation using .iloc on pandas Series
    t0 = time.time()
    kama_slow = np.full(len(close), np.nan)
    kama_slow[0] = close.iloc[0]
    for i in range(1, len(close)):
        s = sc.iloc[i]
        kama_slow[i] = kama_slow[i - 1] + (s * (close.iloc[i] - kama_slow[i - 1]) if not np.isnan(s) else 0.0)
    t1 = time.time()
    slow_time = t1 - t0

    # Fast implementation using extracted NumPy 1D arrays
    t2 = time.time()
    c_arr = close.to_numpy()
    sc_arr = sc.to_numpy()
    n_len = len(c_arr)
    kama_fast = np.full(n_len, np.nan, dtype=np.float64)
    if n_len > 0:
        kama_fast[0] = c_arr[0]
    for i in range(1, n_len):
        s = sc_arr[i]
        kama_fast[i] = kama_fast[i - 1] + (s * (c_arr[i] - kama_fast[i - 1]) if not np.isnan(s) else 0.0)
    t3 = time.time()
    fast_time = t3 - t2

    # Verify identical output
    assert np.allclose(kama_slow, kama_fast, equal_nan=True)

    # Verify integration with _compute_indicators
    dummy_df = pd.DataFrame({
        "Open": close,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": np.random.randint(100, 1000, N),
    })
    computed = _compute_indicators(dummy_df)
    assert np.allclose(computed["close_kama"].to_numpy(), kama_fast, equal_nan=True)

    print(f"KAMA Slow (.iloc): {slow_time:.5f}s, Fast (NumPy): {fast_time:.5f}s, Speedup: {slow_time/fast_time:.1f}x")
    assert fast_time < slow_time, "NumPy implementation should be faster than pandas .iloc"


if __name__ == "__main__":
    test_perf()
    test_supertrend_perf()
    test_kama_perf()
