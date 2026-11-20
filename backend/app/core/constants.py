"""Application constants and enums."""
from __future__ import annotations

from enum import Enum


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStatus(str, Enum):
    PENDING = "PENDING"
    HIT_TARGET = "HIT_TARGET"
    HIT_STOP = "HIT_STOP"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class MarketRegime(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    PANIC = "PANIC"
    NEUTRAL = "NEUTRAL"
    UNCLEAR = "UNCLEAR"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PLACING = "PLACING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


# NSE Market hours
NSE_OPEN_HOUR = 9
NSE_OPEN_MINUTE = 15
NSE_CLOSE_HOUR = 15
NSE_CLOSE_MINUTE = 30
IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30

# Valid intervals for history
VALID_INTERVALS = {
    "1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "5d", "1wk", "1mo", "3mo"
}
VALID_RANGES = {
    "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
}

# Default watchlist
DEFAULT_WATCHLIST = [
    {"symbol": "YESBANK.NS", "name": "Yes Bank", "sector": "Banking"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "sector": "Metals"},
    {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "sector": "Banking"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power", "sector": "Power"},
    {"symbol": "SBIN.NS", "name": "SBI", "sector": "Banking"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "TCS.NS", "name": "TCS", "sector": "IT"},
    {"symbol": "INFY.NS", "name": "Infosys", "sector": "IT"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Banking"},
]

# Seed prices (last-resort fallback only)
SEED_PRICES = {
    "YESBANK.NS": 25.0,
    "TATASTEEL.NS": 170.0,
    "BANKBARODA.NS": 280.0,
    "TATAPOWER.NS": 445.0,
    "SBIN.NS": 830.0,
    "RELIANCE.NS": 2800.0,
    "TCS.NS": 4200.0,
    "INFY.NS": 1850.0,
    "HDFCBANK.NS": 1680.0,
    "ICICIBANK.NS": 1250.0,
}
