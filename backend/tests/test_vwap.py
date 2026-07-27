import pandas as pd
import numpy as np
from backend.signals import _vwap

def test_vwap_normal():
    high = pd.Series([10.0, 12.0, 14.0])
    low = pd.Series([8.0, 10.0, 12.0])
    close = pd.Series([9.0, 11.0, 13.0])
    volume = pd.Series([100, 200, 300])

    expected_vwap = pd.Series([
        9.0,
        ((9.0 * 100) + (11.0 * 200)) / 300,
        ((9.0 * 100) + (11.0 * 200) + (13.0 * 300)) / 600
    ])

    result = _vwap(high, low, close, volume)
    pd.testing.assert_series_equal(result, expected_vwap)

def test_vwap_zero_volume():
    high = pd.Series([10.0, 12.0, 14.0])
    low = pd.Series([8.0, 10.0, 12.0])
    close = pd.Series([9.0, 11.0, 13.0])
    volume = pd.Series([0, 200, 300])

    expected_vwap = pd.Series([
        np.nan,
        11.0,
        12.2
    ])

    result = _vwap(high, low, close, volume)
    pd.testing.assert_series_equal(result, expected_vwap)

def test_vwap_empty_series():
    high = pd.Series(dtype=float)
    low = pd.Series(dtype=float)
    close = pd.Series(dtype=float)
    volume = pd.Series(dtype=float)

    result = _vwap(high, low, close, volume)
    pd.testing.assert_series_equal(result, pd.Series(dtype=float))
