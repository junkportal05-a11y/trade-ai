import pytest
from freezegun import freeze_time

# Import the test function correctly from its new location
from app.services.market_hours import is_nse_market_open

def test_market_open_weekday():
    # Monday, 10:00 AM IST is 4:30 AM UTC
    with freeze_time("2023-10-23 04:30:00"):
        assert is_nse_market_open() is True

def test_market_closed_weekend():
    # Saturday, 10:00 AM IST is 4:30 AM UTC
    with freeze_time("2023-10-21 04:30:00"):
        assert is_nse_market_open() is False

def test_market_closed_before_open():
    # Monday, 9:00 AM IST is 3:30 AM UTC
    with freeze_time("2023-10-23 03:30:00"):
        assert is_nse_market_open() is False

def test_market_closed_after_close():
    # Monday, 4:00 PM IST is 10:30 AM UTC
    with freeze_time("2023-10-23 10:30:00"):
        assert is_nse_market_open() is False

def test_market_exactly_at_open():
    # Monday, 9:15 AM IST is 3:45 AM UTC
    with freeze_time("2023-10-23 03:45:00"):
        assert is_nse_market_open() is True

def test_market_exactly_at_close():
    # Monday, 3:30 PM IST is 10:00 AM UTC
    with freeze_time("2023-10-23 10:00:00"):
        assert is_nse_market_open() is True
