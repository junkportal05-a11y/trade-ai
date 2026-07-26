import pytest
from freezegun import freeze_time
from app.services.market_hours import is_nse_market_open

def test_is_nse_market_open():
    # Monday 9:30 AM IST -> Open
    with freeze_time("2023-01-02 04:00:00"):
        assert is_nse_market_open() is True

    # Monday 9:14 AM IST -> Closed
    with freeze_time("2023-01-02 03:44:00"):
        assert is_nse_market_open() is False

    # Monday 3:30 PM IST -> Open
    with freeze_time("2023-01-02 10:00:00"):
        assert is_nse_market_open() is True

    # Monday 3:31 PM IST -> Closed
    with freeze_time("2023-01-02 10:01:00"):
        assert is_nse_market_open() is False

    # Saturday 12:00 PM IST -> Closed
    with freeze_time("2023-01-07 06:30:00"):
        assert is_nse_market_open() is False

    # Sunday 12:00 PM IST -> Closed
    with freeze_time("2023-01-08 06:30:00"):
        assert is_nse_market_open() is False
