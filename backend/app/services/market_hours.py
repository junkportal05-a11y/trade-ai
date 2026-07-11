"""Market hours utility."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from app.core.constants import (
    NSE_OPEN_HOUR,
    NSE_OPEN_MINUTE,
    NSE_CLOSE_HOUR,
    NSE_CLOSE_MINUTE,
    IST_OFFSET_HOURS,
    IST_OFFSET_MINUTES,
)


def is_nse_market_open() -> bool:
    """NSE market is open Monday-Friday, 9:15 AM to 3:30 PM IST."""
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)

    if now_ist.weekday() >= 5:
        return False

    minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
    start_minutes = NSE_OPEN_HOUR * 60 + NSE_OPEN_MINUTE
    end_minutes = NSE_CLOSE_HOUR * 60 + NSE_CLOSE_MINUTE

    return start_minutes <= minutes_since_midnight <= end_minutes


def get_ist_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)
