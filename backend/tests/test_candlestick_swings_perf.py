import time
import numpy as np
import pandas as pd
from backend.candlestick_patterns import detect_swings

def test_detect_swings_perf():
    np.random.seed(42)
    n = 10000
    prices = np.cumsum(np.random.randn(n)) + 100
    df = pd.DataFrame({
        "Open": prices,
        "High": prices + np.random.rand(n) * 2,
        "Low": prices - np.random.rand(n) * 2,
        "Close": prices + np.random.randn(n)
    })

    start = time.time()
    for _ in range(5):
        sh, sl = detect_swings(df, window=5)
    end = time.time()

    # Check that we got results
    assert len(sh) > 0
    assert len(sl) > 0

    # Just print the time so we know it runs, should be very fast.
    print(f"\ndetect_swings (N=10000) * 5 took {end - start:.4f}s")
