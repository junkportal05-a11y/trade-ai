import pandas as pd
from datetime import timedelta
import pytest
from data_validator import calculate_confidence

def test_perfect_data():
    dates = pd.date_range(start="2023-01-01 09:15:00", periods=5, freq="5min")
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [101, 102, 103, 104, 105],
        'Low': [99, 100, 101, 102, 103],
        'Close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'Volume': [1000, 1500, 1200, 1100, 1300]
    }, index=dates)
    assert calculate_confidence(df) == 100.0

def test_flatlines():
    dates = pd.date_range(start="2023-01-01 09:15:00", periods=5, freq="5min")
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [101, 101, 103, 104, 105],
        'Low': [99, 101, 101, 102, 103],
        'Close': [100.5, 101, 102.5, 103.5, 104.5],
        'Volume': [1000, 1500, 1200, 1100, 1300]
    }, index=dates)
    assert calculate_confidence(df) == 80.0

def test_zero_volume():
    dates = pd.date_range(start="2023-01-01 09:15:00", periods=5, freq="5min")
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [101, 102, 103, 104, 105],
        'Low': [99, 100, 101, 102, 103],
        'Close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'Volume': [1000, 0, 1200, 1100, -10]
    }, index=dates)
    assert calculate_confidence(df) == 60.0

def test_time_gaps():
    dates = [
        pd.Timestamp("2023-01-01 09:15:00"),
        pd.Timestamp("2023-01-01 09:20:00"),
        pd.Timestamp("2023-01-01 09:35:00"),
        pd.Timestamp("2023-01-01 09:40:00"),
        pd.Timestamp("2023-01-01 09:45:00"),
    ]
    df = pd.DataFrame({
        'Open': [100]*5,
        'High': [101]*5,
        'Low': [99]*5,
        'Close': [100.5]*5,
        'Volume': [1000]*5
    }, index=pd.DatetimeIndex(dates))
    assert calculate_confidence(df, interval="5m") == 96.0

def test_overnight_gaps():
    dates = [
        pd.Timestamp("2023-01-01 15:25:00"),
        pd.Timestamp("2023-01-01 15:30:00"),
        pd.Timestamp("2023-01-02 09:15:00"),
        pd.Timestamp("2023-01-02 09:20:00"),
        pd.Timestamp("2023-01-02 09:25:00"),
    ]
    df = pd.DataFrame({
        'Open': [100]*5,
        'High': [101]*5,
        'Low': [99]*5,
        'Close': [100.5]*5,
        'Volume': [1000]*5
    }, index=pd.DatetimeIndex(dates))
    assert calculate_confidence(df, interval="5m") == 100.0

def test_minimum_rows():
    dates = pd.date_range(start="2023-01-01 09:15:00", periods=4, freq="5min")
    df = pd.DataFrame({
        'Open': [100]*4,
        'High': [101]*4,
        'Low': [99]*4,
        'Close': [100.5]*4,
        'Volume': [1000]*4
    }, index=dates)
    assert calculate_confidence(df) == 0.0

def test_no_volume_column():
    dates = pd.date_range(start="2023-01-01 09:15:00", periods=5, freq="5min")
    df = pd.DataFrame({
        'Open': [100]*5,
        'High': [101]*5,
        'Low': [99]*5,
        'Close': [100.5]*5,
    }, index=dates)
    assert calculate_confidence(df) == 100.0

def test_multiple_penalties():
    dates = [
        pd.Timestamp("2023-01-01 09:15:00"),
        pd.Timestamp("2023-01-01 09:20:00"),
        pd.Timestamp("2023-01-01 09:30:00"),
        pd.Timestamp("2023-01-01 09:35:00"),
        pd.Timestamp("2023-01-01 09:40:00"),
    ]
    df = pd.DataFrame({
        'Open': [100, 101, 102, 103, 104],
        'High': [101, 101, 103, 104, 105],
        'Low': [99, 101, 101, 102, 103],
        'Close': [100.5, 101, 102.5, 103.5, 104.5],
        'Volume': [1000, 1500, 0, 1100, 1300]
    }, index=pd.DatetimeIndex(dates))
    assert calculate_confidence(df, interval="5m") == 58.0

def test_lower_bound():
    dates = pd.date_range(start="2023-01-01 09:15:00", periods=5, freq="5min")
    df = pd.DataFrame({
        'Open': [100]*5,
        'High': [100]*5,
        'Low': [100]*5,
        'Close': [100]*5,
        'Volume': [0]*5
    }, index=dates)
    assert calculate_confidence(df) == 0.0
