import pandas as pd

from backend.signals import check_volume_surge


def test_check_volume_surge_insufficient_data():
    df = pd.DataFrame({"Volume": [100] * 10})
    assert not check_volume_surge(df, lookback=20)


def test_check_volume_surge_zero_avg_volume():
    # length=21 to ensure we have >= 20+1
    df = pd.DataFrame({"Volume": [0] * 20 + [100]})
    assert not check_volume_surge(df, lookback=20)


def test_check_volume_surge_surge_present():
    # 20 periods of volume 100, current=120 -> len=21
    df = pd.DataFrame({"Volume": [100] * 20 + [120]})
    assert check_volume_surge(df, lookback=20)

    # Current volume 150 (1.5x)
    df = pd.DataFrame({"Volume": [100] * 20 + [150]})
    assert check_volume_surge(df, lookback=20)


def test_check_volume_surge_no_surge():
    # 20 periods of volume 100, current=119
    df = pd.DataFrame({"Volume": [100] * 20 + [119]})
    assert not check_volume_surge(df, lookback=20)


def test_check_volume_surge_lookback_custom():
    # Custom lookback = 5
    # 5 periods of 100, current=120 -> len=6
    df = pd.DataFrame({"Volume": [100] * 5 + [120]})
    assert check_volume_surge(df, lookback=5)

    # Custom lookback but insufficient data
    df = pd.DataFrame({"Volume": [100] * 4})
    assert not check_volume_surge(df, lookback=5)
