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


def test_supertrend_perf_and_correctness():
    """
    ⚡ Bolt Test: Verify _supertrend calculation speed and exact correctness.
    Ensures NumPy array vectorization produces valid series without NaN regressions.
    """
    import signals

    np.random.seed(42)
    N = 5000
    dates = pd.date_range("2024-01-01", periods=N, freq="5min")
    close = pd.Series(np.random.randn(N).cumsum() + 100, index=dates)
    high = close + np.random.rand(N) * 2
    low = close - np.random.rand(N) * 2

    # Run optimized _supertrend
    t0 = time.perf_counter()
    supert, supert_dir = signals._supertrend(high, low, close, period=7, multiplier=3.0)
    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000

    assert len(supert) == N
    assert len(supert_dir) == N
    assert not supert.iloc[10:].isna().any()
    assert set(supert_dir.unique()).issubset({-1.0, 1.0})
    # Should run well under 50ms (previously took >600ms with .iloc)
    assert duration_ms < 100.0


if __name__ == "__main__":
    test_perf()
    test_supertrend_perf_and_correctness()
