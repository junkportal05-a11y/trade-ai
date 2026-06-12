"""
upstox_feed.py — Upstox API v2 Data Feed & OAuth Handler
────────────────────────────────────────────────────────────────────────────────
Handles OAuth2 token updates, static & dynamic instrument mappings,
historical candles, and real-time JSON quote snappings.
"""

import os
import time
import json
import gzip
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional

# ── API Credentials ───────────────────────────────────────────────────────────
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_SECRET_KEY = os.getenv("UPSTOX_SECRET_KEY", "")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "")

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "upstox_token.json")
access_token: Optional[str] = None

# ── Static Mappings for Watchlisted Symbols ───────────────────────────────────
STATIC_MAP = {
    "RELIANCE":   "NSE_EQ|INE002A01018",
    "TCS":        "NSE_EQ|INE467B01029",
    "HDFCBANK":   "NSE_EQ|INE040A01034",
    "ICICIBANK":  "NSE_EQ|INE090A01021",
    "INFY":       "NSE_EQ|INE009A01021",
    "ITC":        "NSE_EQ|INE154A01025",
    "SBIN":       "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "KOTAKBANK":  "NSE_EQ|INE237A01028",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "AXISBANK":   "NSE_EQ|INE238A01034",
    "LARSEN":     "NSE_EQ|INE018A01030",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "HUL":        "NSE_EQ|INE030A01027",
    "MARUTI":     "NSE_EQ|INE585B01010",
    "SUNPHARMA":  "NSE_EQ|INE044A01036",
    "TITAN":      "NSE_EQ|INE280A01028",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "WIPRO":      "NSE_EQ|INE075A01022",
    "NESTLEIND":  "NSE_EQ|INE239A01016",
    "HCLTECH":    "NSE_EQ|INE860A01027",
    "ONGC":       "NSE_EQ|INE213A01029",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "POWERGRID":  "NSE_EQ|INE752E01010",
    "NTPC":       "NSE_EQ|INE733E01010",
    "M&M":        "NSE_EQ|INE101A01026",
    "TATASTEEL":  "NSE_EQ|INE081A01012",
    "HAL":        "NSE_EQ|INE066F01020",
    "BEL":        "NSE_EQ|INE263A01024",
    "RVNL":       "NSE_EQ|INE415G01027",
    "IREDA":      "NSE_EQ|INE268R01014",
    "HUDCO":      "NSE_EQ|INE031A01017",
    "COALINDIA":  "NSE_EQ|INE522F01014",
    "NHPC":       "NSE_EQ|INE848E01016",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "TATAPOWER":  "NSE_EQ|INE245A01021",
    "BHEL":       "NSE_EQ|INE257A01026",
    "JSWSTEEL":   "NSE_EQ|INE019A01038",
    "HINDALCO":   "NSE_EQ|INE038A01020",
    "CIPLA":      "NSE_EQ|INE059A01026",
    "DRREDDY":    "NSE_EQ|INE089A01023",
    "TECHM":      "NSE_EQ|INE669C01036",
    "LT":         "NSE_EQ|INE018A01030",
    "BAJAJFINSV": "NSE_EQ|INE918I01026",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
}

_DYNAMIC_MAP = {}


# Load token at module import
def load_token() -> Optional[str]:
    global access_token
    # Try DB first (survives Hugging Face deploys)
    try:
        import db

        token = db.get_upstox_token()
        if token:
            access_token = token
            return token
    except Exception:
        pass
    # Fallback: file (local dev only)
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
                access_token = data.get("access_token")
                return access_token
        except Exception:
            pass
    return None


load_token()


_last_token_check = 0
def is_authorized() -> bool:
    global access_token, _last_token_check
    if access_token is None:
        now = time.time()
        if now - _last_token_check > 5:
            _last_token_check = now
            load_token()
    return access_token is not None


def get_login_url(state: str = "") -> str:
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": UPSTOX_API_KEY,
        "redirect_uri": UPSTOX_REDIRECT_URI,
    }
    if state:
        params["state"] = state
    url = f"https://api.upstox.com/v2/login/authorization/dialog?{urlencode(params)}"
    return url


def save_token(token: str, details: dict = None):
    global access_token
    access_token = token
    # Save to DB (persists on Hugging Face Space)
    try:
        import db

        db.save_upstox_token(token, details or {})
    except Exception as e:
        print(f"[Upstox] DB save failed: {e}")
    # Also save to file for local dev
    try:
        payload = {"access_token": token, "updated_at": time.time()}
        if details:
            payload.update(details)
        with open(TOKEN_FILE, "w") as f:
            json.dump(payload, f, indent=4)
    except Exception:
        pass


def exchange_code_for_token(
    code: str, redirect_uri: Optional[str] = None
) -> Optional[dict]:
    url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "accept": "application/json",
    }
    data = {
        "code": code,
        "client_id": UPSTOX_API_KEY,
        "client_secret": UPSTOX_SECRET_KEY,
        "redirect_uri": redirect_uri or UPSTOX_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    try:
        r = requests.post(url, headers=headers, data=data, timeout=15)
        if r.status_code == 200:
            res = r.json()
            token = res.get("access_token")
            if token:
                save_token(token, res)
                return res
        print(f"[Upstox Auth] Token exchange failed ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"[Upstox Auth] Error exchanging token: {e}")
    return None


def get_instrument_key(symbol: str) -> Optional[str]:
    # Clean symbol: remove suffixes like .NS, .BO, :NSE, :BSE
    clean = symbol.upper().split(".")[0].split(":")[0]
    if clean in STATIC_MAP:
        return STATIC_MAP[clean]

    global _DYNAMIC_MAP
    if clean in _DYNAMIC_MAP:
        return _DYNAMIC_MAP[clean]

    # Try loading dynamic cache from disk
    cache_path = os.path.join(os.path.dirname(__file__), "upstox_instruments.json")
    if not _DYNAMIC_MAP and os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                _DYNAMIC_MAP = json.load(f)
        except Exception:
            pass

    if clean in _DYNAMIC_MAP:
        return _DYNAMIC_MAP[clean]

    # Download and extract from GZ master
    try:
        print(
            f"[Upstox Feed] Cache miss for '{symbol}'. Downloading master instruments list..."
        )
        url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
        r = requests.get(url, timeout=10)
        data = gzip.decompress(r.content)
        items = json.loads(data)
        for item in items:
            if item.get("segment") == "NSE_EQ":
                tsym = item.get("trading_symbol")
                if tsym:
                    _DYNAMIC_MAP[tsym.upper()] = item.get("instrument_key")
        # Save cache
        with open(cache_path, "w") as f:
            json.dump(_DYNAMIC_MAP, f)
        return _DYNAMIC_MAP.get(clean)
    except Exception as e:
        print(f"[Upstox Feed] Dynamic mapping failed for {symbol}: {e}")
    return None


def get_historical_candles(
    symbol: str, period_or_range: str, interval: str
) -> Optional[pd.DataFrame]:
    global access_token
    if not access_token:
        return None

    key = get_instrument_key(symbol)
    if not key:
        return None

    # Map interval to Upstox API format
    # Upstox supports: 1minute, 5minute, 10minute, 15minute, 30minute, 60minute, day, week, month
    if interval in ("1m", "1min", "1minute"):
        mapped_int = "1minute"
        resample_rule = None
    elif interval in ("5m", "5min", "5minute"):
        mapped_int = "30minute"
        resample_rule = None
    elif interval in ("10m", "10min", "10minute"):
        mapped_int = "1minute"
        resample_rule = "10min"
    elif interval in ("15m", "15min", "15minute"):
        mapped_int = "1minute"
        resample_rule = "15min"
    elif interval in ("30m", "30min", "30minute"):
        mapped_int = "30minute"
        resample_rule = None
    elif interval in ("1h", "60m", "60min", "60minute", "1hour"):
        mapped_int = "1minute"
        resample_rule = "60min"
    elif interval in ("1d", "day", "1day"):
        mapped_int = "day"
        resample_rule = None
    elif interval in ("1wk", "week", "1week", "wk"):
        mapped_int = "week"
        resample_rule = None
    elif interval in ("1mo", "month", "1month", "mo"):
        mapped_int = "month"
        resample_rule = None
    else:
        mapped_int = "day"
        resample_rule = None

    # Calculate date range
    to_dt = datetime.now(timezone.utc)
    days_back = 5

    # Check if we are requesting daily or longer interval bars
    is_daily_or_longer = mapped_int in ("day", "week", "month")

    if is_daily_or_longer:
        if period_or_range == "1mo":
            days_back = 90  # Fetch 90 days to ensure enough bars (~60 trading days) for indicator warm-up
        elif period_or_range == "3mo":
            days_back = 90
        elif period_or_range == "6mo":
            days_back = 180
        elif period_or_range == "1y":
            days_back = 365
        elif period_or_range == "2y":
            days_back = 365 * 2
        elif period_or_range == "5y":
            days_back = 365 * 5
        elif period_or_range == "max":
            days_back = 365 * 10
        else:
            days_back = 365 * 2
    else:
        # Intraday (1m, 5m, 15m, 30m, 60m)
        if period_or_range == "1d":
            days_back = 1
        elif period_or_range == "5d":
            days_back = 7
        elif period_or_range == "1mo":
            days_back = 30
        else:
            days_back = 10

    from_dt = to_dt - timedelta(days=days_back)
    to_str = to_dt.strftime("%Y-%m-%d")
    from_str = from_dt.strftime("%Y-%m-%d")

    try:
        url = f"https://api.upstox.com/v2/historical-candle/{key}/{mapped_int}/{to_str}/{from_str}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res.get("status") == "success":
                candles = res.get("data", {}).get("candles")
                if not candles:
                    return None

                # Upstox returns candles newest first (reverse chronological order)
                df = pd.DataFrame(
                    candles,
                    columns=["Date", "Open", "High", "Low", "Close", "Volume", "OI"],
                )
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
                df.sort_index(inplace=True)
                df = df.astype(
                    {
                        "Open": float,
                        "High": float,
                        "Low": float,
                        "Close": float,
                        "Volume": float,
                    }
                )

                if resample_rule:
                    df = (
                        df.resample(resample_rule)
                        .agg(
                            {
                                "Open": "first",
                                "High": "max",
                                "Low": "min",
                                "Close": "last",
                                "Volume": "sum",
                                "OI": "last",
                            }
                        )
                        .dropna(subset=["Open"])
                    )

                return df
        print(f"[Upstox Candles] Fetch failed ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"[Upstox Candles] Error fetching candles for {symbol}: {e}")
    return None


def get_live_quotes(symbols: list) -> dict:
    global access_token
    if not access_token:
        return {}

    keys = []
    sym_by_key = {}
    for s in symbols:
        k = get_instrument_key(s)
        if k:
            keys.append(k)
            sym_by_key[k] = s

    if not keys:
        return {}

    try:
        url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={','.join(keys)}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res.get("status") == "success":
                data = res.get("data") or {}
                results = {}
                for key, val in data.items():
                    sym = sym_by_key.get(key)
                    if sym and "last_price" in val:
                        price = float(val["last_price"])
                        ohlc = val.get("ohlc") or {}
                        prev_close = float(ohlc.get("close") or price)
                        open_p = float(ohlc.get("open") or price)
                        high = float(ohlc.get("high") or price)
                        low = float(ohlc.get("low") or price)
                        volume = int(val.get("volume", 0))

                        change = price - prev_close
                        change_pct = (change / prev_close * 100) if prev_close else 0.0

                        results[sym] = {
                            "symbol": sym,
                            "name": val.get("name", sym),
                            "price": round(price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "volume": volume,
                            "open": round(open_p, 2),
                            "high": round(high, 2),
                            "low": round(low, 2),
                            "prev_close": round(prev_close, 2),
                            "source": "upstox",
                            "sector": "NSE Stock",
                        }
                return results
    except Exception as e:
        print(f"[Upstox Quotes] Error: {e}")
    return {}
