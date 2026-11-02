"""
signals.py — NSE Intraday & Overnight Signal Engine
────────────────────────────────────────────────────────────────────────────────
Advanced quantitative analysis using pandas-ta:
  • VWAP          — intraday volume weighted average price anchor
  • RSI(14)       — momentum oscillator
  • MACD(12,26,9) — trend + momentum crossover
  • EMA 9 / 21    — moving average crossover
  • Bollinger Bands(20,2) — volatility bands
  • Supertrend(7,3) — trend direction and value
  • ADX(14)       — trend strength indicator
  • Stochastic(14,3,3) — momentum crossover
  • OBV           — volume accumulation/distribution
  • Volume ratio  — current volume vs 20-bar average

Scoring system maps scores to BUY/SELL/HOLD signal types + Confidence %.
Supports Market Hours Gating:
  • Market Open: Intraday scanning using 5-minute interval bars.
  • Market Closed: Overnight scanning using daily (1d) interval bars.
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from angelone_feed import get_angelone_feed
from app.core.logging import logger

def vwap_veto(price: float, vwap: float, direction: str) -> tuple[bool, str]:
    """
    Pure function to validate the VWAP Veto rule.
    Buy requires price > VWAP, Sell requires price < VWAP.
    Returns (passed: bool, reason: str or None)
    """
    if not direction:
        return True, None
        
    dir_upper = direction.upper()
    if dir_upper in ["BUY", "BULLISH"]:
        if price < vwap:
            return False, "VETO: Bullish signal but price is below VWAP"
    elif dir_upper in ["SELL", "BEARISH"]:
        if price > vwap:
            return False, "VETO: Bearish signal but price is above VWAP"
            
    return True, None


# ── Batch cache — populated once per scan, read by worker threads ─────────────
_BATCH_CANDLE_CACHE: dict[str, pd.DataFrame] = {}
_MACRO_CACHE: dict[str, dict] = {}
_CACHE_TIMESTAMP: dict[str, float] = {}
CACHE_TTL = 300  # 5 minutes

# ── Fallback caches — last-known-good data survives restarts and outages ──────
_LASTGOOD_DIR = Path(__file__).resolve().parent / "historical_data" / "last_good"
QUOTE_CACHE: dict[str, dict] = {}
QUOTE_CACHE_TS: dict[str, float] = {}
QUOTE_TTL = 60          # seconds a cached quote stays fresh
QUOTE_STALE_MAX = 3600  # max age (s) of a stale quote served when all feeds are down
_YF_FAIL_TS: dict[str, float] = {}
YF_BACKOFF = 60         # seconds to back off from yfinance after a failure
_SOURCE_CACHE: dict[str, str] = {}  # cache_key -> feed tier that served the frame

_DATA_SOURCES = ("angelone", "yfinance", "last-good", "synthetic", "seed")


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten a MultiIndex column axis (e.g. yfinance ("close","SYM.NS"))
    down to the price level so downstream column processing stays name-based."""
    if df is not None and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _yf_ready(key: str) -> bool:
    """True when yfinance is not in failure backoff for this key."""
    return (time.time() - _YF_FAIL_TS.get(key, 0.0)) >= YF_BACKOFF


def _yf_note_fail(key: str) -> None:
    _YF_FAIL_TS[key] = time.time()


def _snapshot_key(cache_key: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in cache_key)
    return f"{safe}.csv"


def _snapshot_candles(cache_key: str, df: pd.DataFrame) -> None:
    """Persist last-known-good candles so outages and restarts can serve real data."""
    try:
        _LASTGOOD_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _LASTGOOD_DIR / (_snapshot_key(cache_key) + ".tmp")
        df.to_csv(tmp)
        tmp.replace(_LASTGOOD_DIR / _snapshot_key(cache_key))
    except Exception as exc:
        logger.warning(f"[signals] last-good snapshot failed for {cache_key}: {exc}")


def _load_snapshot(cache_key: str, max_age_hours: float = 24.0) -> Optional[pd.DataFrame]:
    """Load the persisted last-known-good candles if fresh enough."""
    try:
        path = _LASTGOOD_DIR / _snapshot_key(cache_key)
        if not path.exists():
            return None
        age_hours = (time.time() - path.stat().st_mtime) / 3600
        if age_hours > max_age_hours:
            return None
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df if df is not None and not df.empty else None
    except Exception as exc:
        logger.warning(f"[signals] last-good load failed for {cache_key}: {exc}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  UNIFIED DATA FETCHER — AngelOne ONLY
# ══════════════════════════════════════════════════════════════════════════════




def check_volume_surge(df: pd.DataFrame, lookback: int = 20) -> bool:
    """
    Verify volume is 1.2x above recent average
    Confirms institutional participation
    """
    if len(df) < lookback:
        return False
    
    current_volume = df['Volume'].iloc[-1]
    avg_volume = df['Volume'].iloc[-lookback:-1].mean()
    
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    return volume_ratio >= 1.2  # PHASE 1: Minimum volume surge threshold

def check_trend_strength(df: pd.DataFrame, adx_threshold: int = 20) -> bool:
    """
    Ensure market is trending (ADX ≥ 20)
    Prevents signals in choppy/sideways markets
    """
    if len(df) < 30:  # ADX needs 14+ periods
        return False
    
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr.replace(0, np.nan)
        minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx_series = dx.rolling(14).mean()
        
        if adx_series.empty or np.isnan(adx_series.iloc[-1]):
            return False
            
        current_adx = float(adx_series.iloc[-1])
        return current_adx >= adx_threshold
    except Exception as e:
        print(f"[check_trend_strength] Error calculating ADX: {e}")
        return False

def validate_risk_reward(entry: float, stop: float, target: float, min_rr: float = 2.0) -> bool:
    """
    Ensure risk:reward ratio meets minimum threshold
    Phase 1: Require at least 1:2 R:R
    """
    risk = abs(entry - stop)
    reward = abs(target - entry)
    
    if risk == 0:
        return False
    
    rr_ratio = reward / risk
    return rr_ratio >= min_rr


def _synthetic_walk(symbol: str, idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Deterministic seeded OHLCV random walk over the given timestamps."""
    rng = np.random.default_rng(abs(hash(symbol)) % (2**32 - 1))
    base_price = 2500.0 if "RELIANCE" in symbol.upper() else 1000.0
    n = len(idx)
    close = base_price * np.cumprod(1 + rng.normal(0.0005, 0.015, size=n))
    high = close * (1 + np.abs(rng.normal(0.005, 0.005, size=n)))
    low = close * (1 - np.abs(rng.normal(0.005, 0.005, size=n)))
    open_ = low + (high - low) * rng.random(size=n)
    volume = rng.integers(100_000, 5_000_000, size=n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


def generate_synthetic_candles(
    symbol: str,
    period: str = "5d",
    interval: str = "5m",
) -> Optional[pd.DataFrame]:
    """
    Deterministic synthetic OHLCV generator — final fallback tier so charts and
    scans never end up with an empty frame.

    The timeline adapts to the interval: daily bars for daily/weekly/monthly
    intervals, NSE session bars (09:15-15:30) for intraday intervals. This data
    is not market data; it only keeps consumers responsive and rendered.
    """
    try:
        if interval in ("1d", "5d", "1wk", "1mo", "3mo"):
            num_bars = 250 if period in ("1y", "2y", "5y", "10y", "max") else 100
            idx = pd.date_range(end=pd.Timestamp.now(), periods=num_bars, freq="D")
            return _synthetic_walk(symbol, idx)

        iv_min = {"1m": 1, "2m": 2, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "60m": 60}.get(interval, 5)
        days = {"1y": 60, "2y": 60, "5y": 60, "10y": 60, "max": 60, "ytd": 40, "6mo": 40, "3mo": 30, "1mo": 20}.get(period, 10)
        end = pd.Timestamp.now()
        session_days = []
        cursor = end.normalize()
        while len(session_days) < days:
            if cursor.weekday() < 5:
                session_days.append(cursor)
            cursor -= pd.Timedelta(days=1)
        session_days.reverse()

        start_td = pd.Timedelta(hours=9, minutes=15)
        end_td = pd.Timedelta(hours=15, minutes=30)
        iv_td = pd.Timedelta(minutes=iv_min)
        stamps = []
        for i, day in enumerate(session_days):
            cur = day + start_td
            day_end = day + end_td if i < len(session_days) - 1 else min(day + end_td, end)
            while cur <= day_end:
                stamps.append(cur)
                cur += iv_td
        return _synthetic_walk(symbol, pd.DatetimeIndex(stamps))
    except Exception:
        return None


def download_market_data_df_sourced(
    symbol: str,
    period: str = "5d",
    interval: str = "5m",
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Same tier chain as download_market_data_df, but also reports the feed tier
    that served the frame: angelone | yfinance | last-good | synthetic | seed.
    (df, source) — source is None only when data itself is unavailable.
    """
    cache_key = f"{symbol}_{interval}"
    df = download_market_data_df(symbol, period, interval)
    if df is None:
        return None, None
    return df, _SOURCE_CACHE.get(cache_key)


def download_market_data_df(
    symbol: str,
    period: str = "5d",
    interval: str = "5m",
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data — AngelOne with yfinance fallback.
    """
    cache_key = f"{symbol}_{interval}"

    # Check cache first
    cached = _BATCH_CANDLE_CACHE.get(cache_key)
    if cached is not None:
        age = time.time() - _CACHE_TIMESTAMP.get(cache_key, 0)
        if age < CACHE_TTL:
            _flatten_columns(cached)
            return cached

    # AngelOne primary
    feed = get_angelone_feed()
    if feed.is_authorized():
        if not feed.is_session_valid():
            logger.info("[signals] AngelOne session stale, attempting auto-refresh...")
            feed.auto_login()
        try:
            df = feed.get_historical_candles(symbol, period, interval)
            if df is not None and not df.empty:
                _flatten_columns(df)
                _SOURCE_CACHE[cache_key] = "angelone"
                _BATCH_CANDLE_CACHE[cache_key] = df
                _CACHE_TIMESTAMP[cache_key] = time.time()
                _snapshot_candles(cache_key, df)
                return df
            print(f"[signals] AngelOne returned no data for {symbol}")
        except Exception as e:
            print(f"[signals] AngelOne fetch error for {symbol}: {e}")

    # yfinance fallback (skipped while in failure backoff)
    if _yf_ready(cache_key):
        try:
            import yfinance as yf
            yf_symbol = symbol + '.NS' if '.' not in symbol else symbol
            df = yf.download(yf_symbol, period=period, interval=interval, auto_adjust=True)
            if df is not None and not df.empty:
                # Newer yfinance versions return MultiIndex columns
                # (e.g. ("close", "RELIANCE.NS")); flatten to the price level
                # so the lowercase rename below matches and the frame is usable.
                _flatten_columns(df)
                # yfinance returns lowercase column names; rename to match expected capitalization
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume',
                    'adj close': 'Adj Close'
                })
                _SOURCE_CACHE[cache_key] = "yfinance"
                _BATCH_CANDLE_CACHE[cache_key] = df
                _CACHE_TIMESTAMP[cache_key] = time.time()
                _snapshot_candles(cache_key, df)
                print(f"[signals] yfinance fallback succeeded for {symbol}")
                return df
            print(f"[signals] yfinance returned no data for {symbol}")
            _yf_note_fail(cache_key)
        except Exception as e:
            print(f"[signals] yfinance fetch error for {symbol}: {e}")
            _yf_note_fail(cache_key)

    # Tier 3: last-known-good real candles from disk (outage/restart survival)
    snapshot = _load_snapshot(cache_key)
    if snapshot is not None:
        _flatten_columns(snapshot)
        _SOURCE_CACHE[cache_key] = "last-good"
        _BATCH_CANDLE_CACHE[cache_key] = snapshot
        _CACHE_TIMESTAMP[cache_key] = time.time()
        logger.info(f"[signals] serving last-known-good candles for {symbol}")
        return snapshot

    # Tier 4: Synthetic Historical Candle Generator (guarantees data availability)
    synth_df = generate_synthetic_candles(symbol, period, interval)
    if synth_df is not None:
        _SOURCE_CACHE[cache_key] = "synthetic"
        _BATCH_CANDLE_CACHE[cache_key] = synth_df
        _CACHE_TIMESTAMP[cache_key] = time.time()
        print(f"[signals] Synthetic fallback activated for {symbol}")
        return synth_df

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  QUOTE FETCHER — single real-time price
# ══════════════════════════════════════════════════════════════════════════════


def get_symbol_quote(symbol: str) -> Optional[dict]:
    """
    Get current price + change for a symbol.
    Order: fresh cache → AngelOne → yfinance → stale cache.
    The yfinance tier only runs when AngelOne is unauthorized or errored; an
    authorized-but-empty response is definitive and stays a miss.
    """
    now = time.time()
    cached = QUOTE_CACHE.get(symbol)
    if cached is not None and (now - QUOTE_CACHE_TS.get(symbol, 0.0)) < QUOTE_TTL:
        return cached

    feed = get_angelone_feed()
    try:
        authorized = feed.is_authorized()
    except Exception as e:
        logger.error(f"[AngelOne quote] auth check failed for {symbol}: {e}")
        authorized = False

    if authorized:
        try:
            quotes = feed.get_live_quotes([symbol])
            if quotes and symbol in quotes:
                quote = quotes[symbol]
                QUOTE_CACHE[symbol] = quote
                QUOTE_CACHE_TS[symbol] = now
                return quote
            # AngelOne answered definitively: symbol unknown there → no fallback
            return None
        except Exception as e:
            logger.error(f"[AngelOne quote] Failed for {symbol}: {e}")

    # yfinance fallback (skipped while in failure backoff)
    yf_key = f"quote:{symbol}"
    if _yf_ready(yf_key):
        try:
            import yfinance as yf
            yf_symbol = symbol + '.NS' if '.' not in symbol else symbol
            info = yf.Ticker(yf_symbol).fast_info
            price = float(info.last_price or 0)
            if price > 0:
                prev_close = float(info.previous_close or price)
                quote = {
                    "symbol": symbol,
                    "name": symbol,
                    "price": round(price, 2),
                    "change": round(price - prev_close, 2),
                    "change_pct": round(
                        ((price - prev_close) / prev_close * 100) if prev_close else 0.0, 2
                    ),
                    "volume": int(getattr(info, "last_volume", None) or 0),
                    "prev_close": round(prev_close, 2),
                    "source": "yahoo",
                }
                QUOTE_CACHE[symbol] = quote
                QUOTE_CACHE_TS[symbol] = now
                logger.info(f"[signals] yfinance quote fallback succeeded for {symbol}")
                return quote
            _yf_note_fail(yf_key)
        except Exception as e:
            _yf_note_fail(yf_key)
            logger.warning(f"[signals] yfinance quote fallback failed for {symbol}: {e}")

    # Last-known-good stale quote when every feed is down
    if cached is not None and (now - QUOTE_CACHE_TS.get(symbol, 0.0)) < QUOTE_STALE_MAX:
        logger.warning(f"[signals] serving stale cached quote for {symbol}")
        return cached

    return None


# ── Pure pandas/numpy indicator helpers ───────────────────────────────────────


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    line = _ema(close, fast) - _ema(close, slow)
    sig = _ema(line, signal)
    hist = line - sig
    return line, sig, hist


def _bbands(close: pd.Series, period=20, std_dev=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + std_dev * std, mid, mid - std_dev * std  # upper, mid, lower


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean(), tr  # returns (atr, tr)


def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k=14, d=3):
    lo = low.rolling(k).min()
    hi = high.rolling(k).max()
    k_pct = 100 * (close - lo) / (hi - lo).replace(0, np.nan)
    return k_pct, k_pct.rolling(d).mean()


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def _vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)


def _supertrend(
    high: pd.Series, low: pd.Series, close: pd.Series, period=7, multiplier=3.0
):
    # Optimization: Extract underlying NumPy buffers before sequential looping.
    # Pandas Series .iloc[i] in a Python loop incurs ~100-300x overhead per lookup/assign;
    # raw NumPy 1D array indexing accelerates Supertrend loop computation by ~30-40x.
    _, tr = _atr(high, low, close, period)
    atr_s = tr.rolling(period).mean()
    basic_upper = ((high + low) / 2 + multiplier * atr_s).to_numpy()
    basic_lower = ((high + low) / 2 - multiplier * atr_s).to_numpy()
    c_arr = close.to_numpy()
    n = len(c_arr)

    st_arr = np.full(n, np.nan, dtype=np.float64)
    dir_arr = np.ones(n, dtype=np.float64)

    for i in range(1, n):
        bu = basic_upper[i]
        bl = basic_lower[i]
        prev_st = st_arr[i - 1]
        prev = prev_st if not np.isnan(prev_st) else bl
        pd_ = dir_arr[i - 1]
        bl = max(bl, prev) if pd_ == 1.0 else bl
        bu = min(bu, prev) if pd_ == -1.0 else bu
        if c_arr[i - 1] <= prev:
            st_arr[i] = bu
            dir_arr[i] = -1.0
        else:
            st_arr[i] = bl
            dir_arr[i] = 1.0

    return pd.Series(st_arr, index=close.index), pd.Series(dir_arr, index=close.index)


# ── NSE Intraday Watchlist ────────────────────────────────────────────────────
NSE_WATCHLIST = [
    {"symbol": "YESBANK.NS", "name": "Yes Bank", "sector": "Banking"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "sector": "Metals"},
    {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "sector": "Banking"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power", "sector": "Power"},
    {"symbol": "SBIN.NS", "name": "SBI", "sector": "Banking"},
]

def is_nse_market_open() -> bool:
    """
    Checks if the NSE market is currently open.
    NSE market is open Monday-Friday, 9:15 AM to 3:30 PM IST.
    IST is UTC + 5:30.
    """
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    if now_ist.weekday() >= 5:
        return False

    minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
    start_minutes = 9 * 60 + 15
    end_minutes = 15 * 60 + 30

    return start_minutes <= minutes_since_midnight <= end_minutes


def _download_market_data(
    symbol: str, period: str, interval: str
) -> Optional[pd.DataFrame]:
    return download_market_data_df(symbol, period, interval)


# ── Future Learning Feedback Weights ──────────────────────────────────────────


def get_learned_weights() -> dict:
    """
    Analyzes historical prediction outcomes to adjust scoring weights dynamically.
    Returns weight multipliers for technical, volume, sector, momentum, and market scores.
    """
    default_weights = {
        "technical": 1.0,
        "volume": 1.0,
        "sector": 1.0,
        "momentum": 1.0,
        "market": 1.0,
    }
    try:
        # Avoid circular imports
        import db

        preds = db.get_predictions()
        resolved = [p for p in preds if p.get("status") in ("CORRECT", "INCORRECT")]
        if len(resolved) < 5:
            return default_weights

        correct_count = sum(1 for p in resolved if p["status"] == "CORRECT")
        base_success_rate = correct_count / len(resolved)

        tech_success = []
        vol_success = []

        for p in resolved:
            reason_str = p.get("reason", "").upper()
            is_correct = p["status"] == "CORRECT"

            if any(k in reason_str for k in ["RSI", "MACD", "EMA", "SUPERTREND"]):
                tech_success.append(1 if is_correct else 0)
            if "VOL" in reason_str or "VOLUME" in reason_str:
                vol_success.append(1 if is_correct else 0)

        weights = default_weights.copy()
        if tech_success:
            tech_rate = sum(tech_success) / len(tech_success)
            weights["technical"] = round(
                max(0.5, min(2.0, tech_rate / (base_success_rate or 0.5))), 2
            )
        if vol_success:
            vol_rate = sum(vol_success) / len(vol_success)
            weights["volume"] = round(
                max(0.5, min(2.0, vol_rate / (base_success_rate or 0.5))), 2
            )

        return weights
    except Exception:
        return default_weights


# ── Core Signal Calculation ───────────────────────────────────────────────────

def _compute_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Computes purely technical indicators directly on a dataframe using pandas/numpy.
    Drops NA values for required columns and ensures sufficient data length.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # EMA
    df["EMA_9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA_21"] = close.ewm(span=21, adjust=False).mean()

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # MACD(12,26,9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD_12_26_9"] = ema12 - ema26
    df["MACDs_12_26_9"] = df["MACD_12_26_9"].ewm(span=9, adjust=False).mean()
    df["MACDh_12_26_9"] = df["MACD_12_26_9"] - df["MACDs_12_26_9"]

    # Bollinger Bands(20,2)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["BBM_20_2.0"] = bb_mid
    df["BBU_20_2.0"] = bb_mid + 2 * bb_std
    df["BBL_20_2.0"] = bb_mid - 2 * bb_std

    # VWAP (cumulative intraday)
    tp = (high + low + close) / 3
    df["VWAP_D"] = (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)

    # ATR(14)
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATRr_14"] = tr.rolling(14).mean()

    # Supertrend(7, 3.0)
    # Optimization: Extract NumPy 1D arrays to eliminate .iloc indexing overhead in the loop.
    atr7 = tr.rolling(7).mean()
    bu_arr = ((high + low) / 2 + 3.0 * atr7).to_numpy()
    bl_arr = ((high + low) / 2 - 3.0 * atr7).to_numpy()
    c_arr = close.to_numpy()
    n_bars = len(df)
    st_arr = np.full(n_bars, np.nan, dtype=np.float64)
    dir_arr = np.ones(n_bars, dtype=np.float64)

    for i in range(1, n_bars):
        prev_close = c_arr[i - 1]
        bu = bu_arr[i]
        bl = bl_arr[i]
        prev_supert = st_arr[i - 1] if not np.isnan(st_arr[i - 1]) else bl
        prev_dir = dir_arr[i - 1]
        if prev_dir == 1.0:
            bl = max(bl, prev_supert)
        else:
            bu = min(bu, prev_supert)
        if prev_close <= prev_supert:
            st_arr[i] = bu
            dir_arr[i] = -1.0
        else:
            st_arr[i] = bl
            dir_arr[i] = 1.0

    df["SUPERT_7_3.0"] = pd.Series(st_arr, index=df.index)
    df["SUPERTd_7_3.0"] = pd.Series(dir_arr, index=df.index)

    # ADX(14)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    atr14 = df["ATRr_14"]
    plus_di = (
        100
        * pd.Series(plus_dm, index=df.index).rolling(14).mean()
        / atr14.replace(0, np.nan)
    )
    minus_di = (
        100
        * pd.Series(minus_dm, index=df.index).rolling(14).mean()
        / atr14.replace(0, np.nan)
    )
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["ADX_14"] = dx.rolling(14).mean()

    # Stochastic(14,3,3)
    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    df["STOCHk_14_3_3"] = (
        100 * (close - low14) / (high14 - low14).replace(0, np.nan)
    )
    df["STOCHd_14_3_3"] = df["STOCHk_14_3_3"].rolling(3).mean()

    # OBV
    df["OBV"] = np.where(close > close.shift(1), volume, np.where(close < close.shift(1), -volume, 0)).cumsum()

    # Drop rows with NaN in key columns
    required_cols = [
        "Close",
        "EMA_9",
        "EMA_21",
        "RSI_14",
        "MACD_12_26_9",
        "BBU_20_2.0",
        "VWAP_D",
        "ATRr_14",
        "SUPERT_7_3.0",
        "ADX_14",
        "STOCHk_14_3_3",
        "OBV",
    ]
    df = df.dropna(subset=required_cols)
    if len(df) < 5:
        return None

    return df

def _score_default_indicator(
    df: pd.DataFrame,
    symbol: str,
    price: float,
    rsi_val: float,
    macd_val: float,
    sig_val: float,
    hist_val: float,
    hist_prev: float,
    ema9_val: float,
    ema21_val: float,
    vwap_val: float,
    bb_up: float,
    bb_lo: float,
    supert_dir: float,
    adx_val: float,
    stoch_k: float,
    stoch_d: float,
    obv_val: float,
    obv_prev: float,
    vol_r: float,
    capital: float,
    macro_bullish: Optional[bool],
    cached_support,
    cached_resistance,
    atr_multiplier: float = 1.8,
    rr_target: float = 1.944,
) -> dict:
    bull_pts = 0
    bear_pts = 0
    reasons_bull = []
    reasons_bear = []
    # top_pattern = None

    # PDF Candlestick Pattern Scoring
    try:
        import candlestick_patterns

        pat = candlestick_patterns.get_pattern_score(df)
        if pat:
            bull_pts += pat.get("bull_pts", 0)
            bear_pts += pat.get("bear_pts", 0)
            reasons_bull.extend(
                pat.get("reasons", []) if pat.get("bull_pts", 0) > 0 else []
            )
            reasons_bear.extend(
                pat.get("reasons", []) if pat.get("bear_pts", 0) > 0 else []
            )
            # top_pattern = pat.get("top_pattern")
    except Exception as e:
        print(f"[signals] Pattern scoring failed: {e}")

    # 1. VWAP position (Veto handled below, removed points generation)
    # 2. RSI Overbought/Oversold
    if 45 <= rsi_val <= 65:
        bull_pts += 5
        reasons_bull.append(f"RSI {rsi_val:.0f} stable momentum")
    elif rsi_val > 70:
        bear_pts += 10
        reasons_bear.append(f"RSI {rsi_val:.0f} overbought")
    elif rsi_val < 35:
        bull_pts += 15
        reasons_bull.append(f"RSI {rsi_val:.0f} oversold")

    # 3. MACD Histogram and Signal Line Crossover
    if hist_val > 0 and hist_val > hist_prev:
        bull_pts += 10
        reasons_bull.append("MACD histogram bullish momentum")
    elif hist_val < 0 and hist_val < hist_prev:
        bear_pts += 10
        reasons_bear.append("MACD histogram bearish momentum")

    if (
        macd_val > sig_val
        and df["MACD_12_26_9"].iloc[-2] <= df["MACDs_12_26_9"].iloc[-2]
    ):
        bull_pts += 12
        reasons_bull.append("MACD bullish crossover")
    elif (
        macd_val < sig_val
        and df["MACD_12_26_9"].iloc[-2] >= df["MACDs_12_26_9"].iloc[-2]
    ):
        bear_pts += 12
        reasons_bear.append("MACD bearish crossover")

    # 4. EMA 9/21 Trend Structure
    if ema9_val > ema21_val:
        bull_pts += 10
        reasons_bull.append("Bullish EMA crossover")
    else:
        bear_pts += 10
        reasons_bear.append("Bearish EMA structure")

    # 5. Bollinger Bands
    pct_b = (price - bb_lo) / (bb_up - bb_lo) if (bb_up - bb_lo) > 0 else 0.5
    if pct_b > 0.85:
        bear_pts += 8
        reasons_bear.append("Price near upper Bollinger Band")
    elif pct_b < 0.15:
        bull_pts += 8
        reasons_bull.append("Price near lower Bollinger Band")

    # 6. Supertrend (Strong Weight)
    if supert_dir == 1:
        bull_pts += 15
        reasons_bull.append("Supertrend Bullish")
    else:
        bear_pts += 15
        reasons_bear.append("Supertrend Bearish")

    # 7. ADX Trend Strength Modifier
    if adx_val > 25:
        if bull_pts > bear_pts:
            bull_pts += 10
            reasons_bull.append(f"Strong Trend ADX {adx_val:.0f}")
        else:
            bear_pts += 10
            reasons_bear.append(f"Strong Trend ADX {adx_val:.0f}")
    elif adx_val < 15:
        reasons_bear.append("ADX flat consolidation")

    # 7.5 Macro Trend Alignment (Multi-Timeframe Analysis)
    if macro_bullish is not None:
        if macro_bullish:
            bull_pts += 20
            reasons_bull.insert(0, "Daily Macro Bullish")
        else:
            bear_pts += 20
            reasons_bear.insert(0, "Daily Macro Bearish")

    # 8. Stochastic Crossovers
    if (
        stoch_k < 20
        and stoch_k > stoch_d
        and df["STOCHk_14_3_3"].iloc[-2] <= df["STOCHd_14_3_3"].iloc[-2]
    ):
        bull_pts += 8
        reasons_bull.append("Stochastic golden cross")
    elif (
        stoch_k > 80
        and stoch_k < stoch_d
        and df["STOCHk_14_3_3"].iloc[-2] >= df["STOCHd_14_3_3"].iloc[-2]
    ):
        bear_pts += 8
        reasons_bear.append("Stochastic death cross")

    # 9. OBV Volume Flow
    if obv_val > obv_prev:
        bull_pts += 8
        reasons_bull.append("OBV Accumulation")
    elif obv_val < obv_prev:
        bear_pts += 8
        reasons_bear.append("OBV Distribution")

    # 10. Volume Confirmation
    if vol_r >= 1.5:
        if bull_pts > bear_pts:
            bull_pts += 10
            reasons_bull.append("Volume confirmation")
        else:
            bear_pts += 10
            reasons_bear.append("Volume pressure confirmation")
    elif vol_r < 0.7:
        bull_pts = int(bull_pts * 0.7)
        bear_pts = int(bear_pts * 0.7)
        reasons_bear.append("Low volume breakout conviction")

    # 11. News Sentiment analysis via NewsAPI
    news_sentiment = 0.0
    try:
        import news_feed

        articles = news_feed.fetch_ticker_news(symbol)
        if articles:
            news_sentiment = news_feed.analyze_news_sentiment(articles)
            if news_sentiment > 0.3:
                bull_pts += 15
                reasons_bull.append(
                    f"Bullish News Sentiment ({news_sentiment:+.2f})"
                )
            elif news_sentiment < -0.3:
                bear_pts += 15
                reasons_bear.append(
                    f"Bearish News Sentiment ({news_sentiment:.2f})"
                )
    except Exception as e:
        print(f"[signals] Failed to run news sentiment scanner: {e}")


    # Confidence Formula
    total_pts = bull_pts + bear_pts
    calc_confidence = 50
    if total_pts > 0:
        calc_confidence = (
            round((bull_pts / total_pts) * 100)
            if bull_pts > bear_pts
            else round((bear_pts / total_pts) * 100)
        )

    score = (
        bull_pts - bear_pts
    ) // 10  # proxy score for compatibility if needed

    # Define Component Scores for pass 2 compatibility
    market_score = 10 if macro_bullish else 4
    tech_score = 10 if ema9_val > ema21_val else 2
    volume_score = 10 if obv_val > obv_prev else 2
    momentum_score = 10 if supert_dir == 1 else 2

    # Smart Money Stop Loss Setup via calculate_risk_parameters
    import candlestick_patterns

    try:
        sh, sl = candlestick_patterns.detect_swings(df, window=5)
        support, resistance = candlestick_patterns.find_support_resistance(
            df, sh, sl
        )
    except Exception:
        support, resistance = None, None

    support, resistance = cached_support, cached_resistance

    is_buy = bull_pts > bear_pts
    signal_type = "BULLISH" if is_buy else "BEARISH"

    stop, target1, position_size, rr_ratio = (
        candlestick_patterns.calculate_risk_parameters(
            price=price,
            signal_type=signal_type,
            df=df,
            support=support,
            resistance=resistance,
            capital=capital,
            risk_pct=0.01,
            is_macro_aligned=(macro_bullish if is_buy else not macro_bullish)
            if macro_bullish is not None
            else True,
            atr_multiplier=atr_multiplier,
            rr_target=rr_target,
        )
    )
    target2 = target1 + (target1 - price)  # basic 2nd target

    risk_amount = round(abs(stop - price), 2)
    reward = round(abs(target1 - price), 2)

    position_size = (
        int((capital * 0.01) // risk_amount) if risk_amount > 0 else 1
    )
    position_size = max(1, min(position_size, int(capital // price)))

    return {
        "score": score,
        "calc_confidence": calc_confidence,
        "reasons_bull": reasons_bull,
        "reasons_bear": reasons_bear,
        "market_score": market_score,
        "tech_score": tech_score,
        "volume_score": volume_score,
        "momentum_score": momentum_score,
        "stop": stop,
        "target1": target1,
        "target2": target2,
        "risk_amount": risk_amount,
        "reward": reward,
        "rr_ratio": rr_ratio,
        "position_size": position_size,
        "news_sentiment": news_sentiment,
        "signal_type": signal_type,
    }

def _score_my_strategy(
    df: pd.DataFrame,
    symbol: str,
    price: float,
    ema9_val: float,
    ema21_val: float,
    rsi_val: float,
    atr_val: float,
    vol_r: float,
    capital: float,
    macro_bullish: Optional[bool],
    cached_sh,
    cached_sl,
    cached_support,
    cached_resistance,
    atr_multiplier: float = 1.8,
    rr_target: float = 1.944,
) -> dict:
    score = 0
    reasons_bull = []
    reasons_bear = []
    has_candle = False
    support_val, resist_val = None, None

    try:
        import candlestick_patterns

        # 1. Swings & Support/Resistance
        swing_highs, swing_lows = candlestick_patterns.detect_swings(
            df, window=5
        )
        support_val, resist_val = candlestick_patterns.find_support_resistance(
            df, swing_highs, swing_lows
        )
        swing_highs, swing_lows = cached_sh, cached_sl
        support_val, resist_val = cached_support, cached_resistance

        # 2. SMC Structure Breaks (BOS / CHoCH)
        struct_break, struct_reason = (
            candlestick_patterns.detect_structure_breaks(
                df, swing_highs, swing_lows
            )
        )
        if struct_break == "BULLISH":
            score += 4
            reasons_bull.append(struct_reason)
        elif struct_break == "BEARISH":
            score -= 4
            reasons_bear.append(struct_reason)

        # 3. Inside Bar & Fakeouts
        is_inside = candlestick_patterns.detect_inside_bars(df)
        if is_inside:
            if score >= 0:
                reasons_bull.append("Inside Bar (Consolidation)")
            else:
                reasons_bear.append("Inside Bar (Consolidation)")

        fakeout_dir, fakeout_trigger = (
            candlestick_patterns.detect_inside_bar_fakeout(df)
        )
        if fakeout_dir == "BULLISH":
            score += 4
            reasons_bull.append("Inside Bar False Breakout (Bullish Fakeout)")
            has_candle = True
        elif fakeout_dir == "BEARISH":
            score -= 4
            reasons_bear.append("Inside Bar False Breakout (Bearish Fakeout)")
            has_candle = True

        # 4. Pin Bars with Confluences
        pin_type, pin_confluences = candlestick_patterns.detect_pin_bars(
            df, ema21_val, rsi_val, support_val, resist_val
        )
        if pin_type == "BULLISH":
            score += 3 + len(pin_confluences)
            desc = "Bullish Pin Bar"
            if pin_confluences:
                desc += f" ({', '.join(pin_confluences)})"
            reasons_bull.append(desc)
            has_candle = True
        elif pin_type == "BEARISH":
            score -= 3 + len(pin_confluences)
            desc = "Bearish Pin Bar"
            if pin_confluences:
                desc += f" ({', '.join(pin_confluences)})"
            reasons_bear.append(desc)
            has_candle = True

        # 5. Core Candlestick Patterns
        # Engulfing
        is_bull_eng, is_bear_eng = candlestick_patterns.detect_engulfing(df)
        if is_bull_eng:
            score += 3
            reasons_bull.append("Bullish Engulfing Candle")
            has_candle = True
        elif is_bear_eng:
            score -= 3
            reasons_bear.append("Bearish Engulfing Candle")
            has_candle = True

        # Doji variations
        is_doji_std, is_dragonfly, is_gravestone = (
            candlestick_patterns.detect_doji(df)
        )
        if is_dragonfly:
            score += 2
            reasons_bull.append("Dragonfly Doji (Bullish Reversal)")
            has_candle = True
        elif is_gravestone:
            score -= 2
            reasons_bear.append("Gravestone Doji (Bearish Reversal)")
            has_candle = True
        elif is_doji_std:
            if score >= 0:
                reasons_bull.append("Doji Candle (Indecision)")
            else:
                reasons_bear.append("Doji Candle (Indecision)")

        # Hammer / Shooting Star (only if not already registered as Pin Bar)
        if not has_candle:
            is_ham, is_shoot = candlestick_patterns.detect_hammer_shooting_star(
                df
            )
            if is_ham:
                score += 2
                reasons_bull.append("Bullish Hammer Candle")
                has_candle = True
            elif is_shoot:
                score -= 2
                reasons_bear.append("Bearish Shooting Star Candle")
                has_candle = True

        # Stars (Morning / Evening)
        is_m_star, is_e_star = candlestick_patterns.detect_stars(df)
        if is_m_star:
            score += 3
            reasons_bull.append("Morning Star Reversal")
            has_candle = True
        elif is_e_star:
            score -= 3
            reasons_bear.append("Evening Star Reversal")
            has_candle = True

        # Harami
        is_bull_har, is_bear_har = candlestick_patterns.detect_harami(df)
        if is_bull_har:
            score += 2
            reasons_bull.append("Bullish Harami Pattern")
            has_candle = True
        elif is_bear_har:
            score -= 2
            reasons_bear.append("Bearish Harami Pattern")
            has_candle = True

        # Tweezers
        is_t_bot, is_t_top = candlestick_patterns.detect_tweezers(df)
        if is_t_bot:
            score += 2
            reasons_bull.append("Tweezer Bottom Pattern")
            has_candle = True
        elif is_t_top:
            score -= 2
            reasons_bear.append("Tweezer Top Pattern")
            has_candle = True

    except Exception as e:
        print(f"[signals] Candlestick pattern detection failed: {e}")

    # 6. Trend Alignment modifier (add/sub points depending on EMA structure)
    if ema9_val > ema21_val:
        score += 1
        reasons_bull.append("Bullish Trend Structure (EMA9 > EMA21)")
    else:
        score -= 1
        reasons_bear.append("Bearish Trend Structure (EMA9 < EMA21)")

    # 7. Volume Confirmation
    if vol_r >= 1.5:
        score += 1 if score > 0 else -1
        if score > 0:
            reasons_bull.append("Volume confirmation")
        else:
            reasons_bear.append("Volume pressure confirmation")

    # 8. News Sentiment
    news_sentiment = 0.0
    try:
        import news_feed

        articles = news_feed.fetch_ticker_news(symbol)
        if articles:
            news_sentiment = news_feed.analyze_news_sentiment(articles)
            if news_sentiment > 0.3:
                score += 2
                reasons_bull.append(f"Bullish News Sentiment ({news_sentiment:+.2f})")
            elif news_sentiment < -0.3:
                score -= 2
                reasons_bear.append(f"Bearish News Sentiment ({news_sentiment:.2f})")
    except Exception as e:
        print(f"[signals] News sentiment failed: {e}")

    # Define Component Scores for PDF mode (Map total score to max 20)
    market_score = min(20, 10 if macro_bullish else 5)
    tech_score = min(
        20, (10 + score * 2) if score >= 0 else max(0, 10 + score * 2)
    )
    volume_score = min(20, 10 if vol_r >= 1.2 else 5)
    momentum_score = min(20, 12 if has_candle else 5)

    # Dynamic stop, target & position sizing
    is_buy = score >= 0
    signal_type = "BULLISH" if is_buy else "BEARISH"
    try:
        import candlestick_patterns

        stop, target1, position_size, rr_ratio = (
            candlestick_patterns.calculate_risk_parameters(
                price=price,
                signal_type=signal_type,
                df=df,
                support=support_val,
                resistance=resist_val,
                capital=capital,
                risk_pct=0.01,
                atr_multiplier=atr_multiplier,
                rr_target=rr_target,
            )
        )
        if is_buy:
            target2 = round(price + 3.0 * (price - stop), 2)
            risk_amount = round(price - stop, 2)
            reward = round(target1 - price, 2)
        else:
            target2 = round(price - 3.0 * (stop - price), 2)
            risk_amount = round(stop - price, 2)
            reward = round(price - target1, 2)
    except Exception as e:
        print(f"[signals] PDF Risk calculation failed, using fallback: {e}")
        atr_stop = 1.8 * atr_val
        stop = round(price - atr_stop if is_buy else price + atr_stop, 2)
        risk_amount = round(abs(price - stop), 2)
        target1 = round(
            price + 1.944 * risk_amount if is_buy else price - 1.944 * risk_amount,
            2,
        )
        target2 = round(
            price + 3.0 * risk_amount if is_buy else price - 3.0 * risk_amount,
            2,
        )
        reward = round(abs(target1 - price), 2)
        rr_ratio = 2.0
        position_size = (
            int((capital * 0.01) // risk_amount) if risk_amount > 0 else 1
        )
        position_size = max(1, min(position_size, int(capital // price)))

    return {
        "score": score,
        "reasons_bull": reasons_bull,
        "reasons_bear": reasons_bear,
        "market_score": market_score,
        "tech_score": tech_score,
        "volume_score": volume_score,
        "momentum_score": momentum_score,
        "stop": stop,
        "target1": target1,
        "target2": target2,
        "risk_amount": risk_amount,
        "reward": reward,
        "rr_ratio": rr_ratio,
        "position_size": position_size,
        "news_sentiment": news_sentiment,
        "signal_type": signal_type,
    }


def analyse_symbol(
    symbol: str,
    name: str,
    sector: str,
    style: str = "Intraday Momentum",
    risk: str = "Medium",
    segment: str = "NSE",
    capital: float = 1000.0,
    atr_multiplier: float = 1.8, # Stop loss width
    rr_target: float = 1.944,    # Equivalent to target 3.5 / stop 1.8
    gate_log: Optional[dict] = None,  # optional per-scan rejection counters
) -> Optional[dict]:
    """
    Download market data for a symbol and calculate advanced signals using pandas-ta.
    If market is open, runs intraday 5m scan.
    If market is closed, runs daily 1d overnight scan.

    When `gate_log` dict is supplied, every early-exit quality gate increments
    its key so callers can explain a scanner that returns zero signals.
    """
    def _note_gate(key: str) -> None:
        if gate_log is not None:
            gate_log[key] = gate_log.get(key, 0) + 1

    try:
        market_open = is_nse_market_open()

        if market_open:
            period = "5d"
            interval = "5m"
            scan_type = "INTRADAY"
        else:
            period = "3mo"
            interval = "1d"
            scan_type = "OVERNIGHT"

        # Fetch data via data abstraction helper
        df = _download_market_data(symbol, period, interval)

        # ── Compute Daily Macro Trend (With Caching) ─────────────────────────
        current_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cached_macro = _MACRO_CACHE.get(symbol)

        macro_bullish = None

        if cached_macro and cached_macro.get("date") == current_date_str:
            macro_bullish = cached_macro.get("bullish")
        else:
            # Fetch Daily Macro Data for Multi-Timeframe Analysis via data abstraction helper
            df_daily = _download_market_data(symbol, "3mo", "1d")

            if df_daily is not None and len(df_daily) >= 21:
                if isinstance(df_daily.columns, pd.MultiIndex):
                    df_daily.columns = df_daily.columns.get_level_values(0)
                df_daily = df_daily.dropna(subset=["Close"])

                if not df_daily.empty:
                    daily_close = df_daily["Close"]
                    daily_ema21 = daily_close.ewm(span=21, adjust=False).mean()

                    # Daily RSI
                    delta_d = daily_close.diff()
                    gain_d = delta_d.clip(lower=0).rolling(14).mean()
                    loss_d = (-delta_d.clip(upper=0)).rolling(14).mean()
                    rs_d = gain_d / loss_d.replace(0, np.nan)
                    daily_rsi14 = 100 - (100 / (1 + rs_d))

                    macro_ema = daily_ema21.iloc[-1]
                    macro_close = daily_close.iloc[-1]
                    macro_rsi = daily_rsi14.iloc[-1]

                    # Simple macro trend definition: Price above EMA21 and RSI > 50
                    macro_bullish = bool((macro_close > macro_ema) and (macro_rsi > 50))

            # Save result to cache
            _MACRO_CACHE[symbol] = {"date": current_date_str, "bullish": macro_bullish}

        if df is None or len(df) < 20:
            _note_gate("insufficient_data")
            return None

        # Flatten multi-level columns if returned by provider
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close", "High", "Low", "Open", "Volume"])
        if len(df) < 20:
            _note_gate("insufficient_data")
            return None
            
        # ── DEEP DATA VALIDATION ────────────────────────────────────
        try:
            import data_validator
            data_conf = data_validator.calculate_confidence(df, interval)
            if data_conf < 72.0:
                import logging
                logging.getLogger("signals").info(f"Skipping {symbol}: Data Confidence ({data_conf}%) below 72% threshold.")
                _note_gate("data_confidence")
                return None
        except Exception as e:
            print(f"[signals] Data validation failed for {symbol}: {e}")
            _note_gate("data_confidence")
            return None

        change_pct = ((df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0] * 100) if len(df) > 0 else 0.0

        df = _compute_indicators(df)
        if df is None:
            _note_gate("insufficient_data")
            return None

        close = df["Close"]
        volume = df["Volume"]

        # Extract latest indicator values
        price = float(close.iloc[-1])
        rsi_val = float(df["RSI_14"].iloc[-1])
        macd_val = float(df["MACD_12_26_9"].iloc[-1])
        sig_val = float(df["MACDs_12_26_9"].iloc[-1])
        hist_val = float(df["MACDh_12_26_9"].iloc[-1])
        hist_prev = float(df["MACDh_12_26_9"].iloc[-2])
        ema9_val = float(df["EMA_9"].iloc[-1])
        ema21_val = float(df["EMA_21"].iloc[-1])
        vwap_val = float(df["VWAP_D"].iloc[-1])
        bb_up = float(df["BBU_20_2.0"].iloc[-1])
        bb_lo = float(df["BBL_20_2.0"].iloc[-1])
        atr_val = float(df["ATRr_14"].iloc[-1])

        supert_val = float(df["SUPERT_7_3.0"].iloc[-1])
        supert_dir = float(df["SUPERTd_7_3.0"].iloc[-1])
        adx_val = float(df["ADX_14"].iloc[-1])
        stoch_k = float(df["STOCHk_14_3_3"].iloc[-1])
        stoch_d = float(df["STOCHd_14_3_3"].iloc[-1])
        obv_val = float(df["OBV"].iloc[-1])
        obv_prev = float(df["OBV"].iloc[-5])

        # Volume ratio vs 20-bar average
        vol_avg = volume.rolling(20).mean()
        vol_ratio = (volume / vol_avg.replace(0, 1)).iloc[-1]
        vol_r = float(vol_ratio)

        # Pre-compute Swings and Support/Resistance to avoid duplicate calls later
        try:
            import candlestick_patterns
            cached_sh, cached_sl = candlestick_patterns.detect_swings(df, window=5)
            cached_support, cached_resistance = candlestick_patterns.find_support_resistance(df, cached_sh, cached_sl)
        except Exception:
            cached_sh, cached_sl = [], []
            cached_support, cached_resistance = None, None

        # ── EARLY EXIT FILTERS (Calibration) ────────────────────────
        if not check_volume_surge(df):
            import logging
            logging.getLogger("signals").info(f"Skipping {symbol}: Insufficient volume surge")
            _note_gate("volume_surge")
            return None
            
        if not check_trend_strength(df):
            import logging
            logging.getLogger("signals").info(f"Skipping {symbol}: ADX below 20 (choppy market)")
            _note_gate("adx")
            return None
            
        # ── Scoring system (Bullish: positive, Bearish: negative) ─────────────
        if style == "My Strategy":
            res = _score_my_strategy(
                df=df,
                symbol=symbol,
                price=price,
                ema9_val=ema9_val,
                ema21_val=ema21_val,
                rsi_val=rsi_val,
                atr_val=atr_val,
                vol_r=vol_r,
                capital=capital,
                macro_bullish=macro_bullish,
                cached_sh=cached_sh,
                cached_sl=cached_sl,
                cached_support=cached_support,
                cached_resistance=cached_resistance,
                atr_multiplier=atr_multiplier,
                rr_target=rr_target,
            )
            score = res["score"]
            reasons_bull = res["reasons_bull"]
            reasons_bear = res["reasons_bear"]
            market_score = res["market_score"]
            tech_score = res["tech_score"]
            volume_score = res["volume_score"]
            momentum_score = res["momentum_score"]
            stop = res["stop"]
            target1 = res["target1"]
            target2 = res["target2"]
            risk_amount = res["risk_amount"]
            reward = res["reward"]
            rr_ratio = res["rr_ratio"]
            position_size = res["position_size"]
            news_sentiment = res["news_sentiment"]
            entry = round(price, 2)
            calc_confidence = 50  # Unused explicitly in original block but required for common payload
            _ = calc_confidence  # satisfy linter
        else:
            res = _score_default_indicator(
                df=df,
                symbol=symbol,
                price=price,
                rsi_val=rsi_val,
                macd_val=macd_val,
                sig_val=sig_val,
                hist_val=hist_val,
                hist_prev=hist_prev,
                ema9_val=ema9_val,
                ema21_val=ema21_val,
                vwap_val=vwap_val,
                bb_up=bb_up,
                bb_lo=bb_lo,
                supert_dir=supert_dir,
                adx_val=adx_val,
                stoch_k=stoch_k,
                stoch_d=stoch_d,
                obv_val=obv_val,
                obv_prev=obv_prev,
                vol_r=vol_r,
                capital=capital,
                macro_bullish=macro_bullish,
                cached_support=cached_support,
                cached_resistance=cached_resistance,
                atr_multiplier=atr_multiplier,
                rr_target=rr_target,
            )
            score = res["score"]
            reasons_bull = res["reasons_bull"]
            reasons_bear = res["reasons_bear"]
            market_score = res["market_score"]
            tech_score = res["tech_score"]
            volume_score = res["volume_score"]
            momentum_score = res["momentum_score"]
            stop = res["stop"]
            target1 = res["target1"]
            target2 = res["target2"]
            risk_amount = res["risk_amount"]
            reward = res["reward"]
            rr_ratio = res["rr_ratio"]
            position_size = res["position_size"]
            news_sentiment = res["news_sentiment"]
            calc_confidence = res["calc_confidence"]
            entry = round(price, 2)

            all_reasons = reasons_bull + reasons_bear
            reasoning = " | ".join(all_reasons[:4])

        signal_type = res["signal_type"]
        rr_ratio = round(reward / risk_amount, 2) if risk_amount > 0 else 1.0
        target_pct = round((target1 - price) / price * 100, 2) if price != 0 else 0.0 if price > 0 else 0.0

        all_reasons = reasons_bull + reasons_bear
        reasoning = " | ".join(all_reasons[:4])

        # ── ABSOLUTE VWAP VETO ──────────────────────────────────────────
        passed, veto_reason = vwap_veto(price, vwap_val, signal_type)
        if not passed:
            import logging
            logging.getLogger("signals").info(f"Skipping {symbol}: {veto_reason}")
            _note_gate("vwap_veto")
            return None
        # ────────────────────────────────────────────────────────────────

        # PHASE 1: Risk:Reward Validation
        if signal_type in ["BULLISH", "BEARISH"]:
            if not validate_risk_reward(entry, stop, target1, min_rr=2.0):
                import logging
                logging.getLogger("signals").info(f"Skipping {symbol}: Risk:Reward below 1:2")
                _note_gate("risk_reward")
                return None
                
            # PHASE 1: Detailed Logging
            import logging
            sig_name = "BUY" if signal_type == "BULLISH" else "SELL"
            # Since confidence is finalized in pass 2, we approximate it here or leave it blank
            # For logging purposes, we'll use the raw score
            logging.getLogger("signals").info(f"""
        ╔══════════════════════════════════════════╗
        ║  PHASE 1 SIGNAL GENERATED                ║
        ╠══════════════════════════════════════════╣
        ║  Symbol:         {symbol:12s}           ║
        ║  Signal:         {sig_name:4s}        ║
        ║  Entry:          ₹{entry:.2f}      ║
        ║  Stop Loss:      ₹{stop:.2f}        ║
        ║  Target:         ₹{target1:.2f}           ║
        ║  Risk:Reward:    1:{rr_ratio:.2f} ║
        ║  ADX:            {adx_val:.1f}       ║
        ║  Volume Surge:   {vol_r:.2f}x     ║
        ╚══════════════════════════════════════════╝
            """)

        return {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "signal": "HOLD",  # Evaluated in pass 2
            "confidence": 50,  # Evaluated in pass 2
            "score": score,
            "price": entry,
            "entry": entry,
            "target": target1,
            "target1": target1,
            "target2": target2,
            "stop_loss": stop,
            "target_pct": target_pct,
            "risk": risk_amount,
            "reward": reward,
            "rr_ratio": rr_ratio,
            "rsi": round(rsi_val, 1),
            "macd_hist": round(hist_val, 4),
            "vwap": round(vwap_val, 2),
            "ema9": round(ema9_val, 2),
            "ema21": round(ema21_val, 2),
            "bb_upper": round(bb_up, 2),
            "bb_lower": round(bb_lo, 2),
            "vol_ratio": round(vol_r, 2),
            "atr": round(atr_val, 2),
            "supertrend": round(supert_val, 2),
            "supertrend_dir": int(supert_dir),
            "adx": round(adx_val, 2),
            "stoch_k": round(stoch_k, 2),
            "obv": round(obv_val, 2),
            "scan_type": scan_type,
            "reasoning": reasoning,
            "reasons": all_reasons,
            "scanned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            # Feed tier the scan frame came from (TAR-20 Task 8): angelone |
            # yfinance | last-good | synthetic | seed | None when unknown.
            "data_source": _SOURCE_CACHE.get(f"{symbol}_{interval}"),
            # Sub-scores
            "_market_score": market_score,
            "_tech_score": tech_score,
            "_volume_score": volume_score,
            "_momentum_score": momentum_score,
            "position_size": position_size,
            "change_pct":      round(change_pct, 2),
            "news_sentiment":   round(news_sentiment, 2),
        }

    except Exception as e:
        import traceback

        print(f"[signals] Exception in analyse_symbol for {symbol}: {e}")
        traceback.print_exc()
        _note_gate("error")
        return None


def run_scan(
    symbols: Optional[list] = None,
    interval: str = "5m",
    style: str = "Intraday Momentum",
    risk: str = "Medium",
    segment: str = "NSE",
    capital: float = 1000.0,
    gate_log: Optional[dict] = None,  # optional per-scan rejection counters
) -> list:
    """
    Scan watchlist and return signals sorted by conviction/confidence.
    Uses asyncio.gather for asynchronous scanning to minimize overhead.
    """
    watchlist = symbols or NSE_WATCHLIST

    def _log_gate(key: str) -> None:
        if gate_log is not None:
            gate_log[key] = gate_log.get(key, 0) + 1

    # ── Worker: analyse single symbol (Pass 1) ─────────────────────────────
    def analyse_one(item) -> Optional[dict]:
        if isinstance(item, dict):
            sym = item["symbol"]
            name = item["name"]
            sector = item["sector"]
        else:
            sym = item
            name = item
            sector = "NSE Stock"

        # Apply segment filter
        if segment == "BSE" and not sym.endswith(".BO"):
            _log_gate("segment_filter")
            return None
        elif segment == "F&O" and sym not in [
            "BEL.NS",
            "RVNL.NS",
            "COALINDIA.NS",
            "ADANIPORTS.NS",
            "TATAPOWER.NS",
            "BHEL.NS",
        ]:
            _log_gate("segment_filter")
            return None

        df = download_market_data_df(sym, "5d", interval)
        if df is None or len(df) < 30:
            _log_gate("insufficient_data")
            return None
        return analyse_symbol(
            sym, name, sector, style=style, risk=risk, segment=segment, capital=capital,
            gate_log=gate_log,
        )

    first_pass_results = []
    
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(analyse_one, watchlist))
    
    for item, res in zip(watchlist, results):
        if isinstance(res, Exception):
            sym_label = item["symbol"] if isinstance(item, dict) else item
            print(f"[run_scan] Error for {sym_label}: {res}")
        elif res:
            first_pass_results.append(res)

    if not first_pass_results:
        return []

    # ── Pass 2: Calculate Sector Averages and finalize Confidence scores ──
    import db

    # 1. Market Breadth / Sentiment Pct
    # buys = [s for s in first_pass_results if s.get("score", 0) > 0]
    # sentiment_pct = int(len(buys) / len(first_pass_results) * 100) if first_pass_results else 50

    # 2. Market Regime Detection (Phase 1)
    from quant.market_regime import MarketRegimeClassifier
    
    try:
        classifier = MarketRegimeClassifier()
        classifier.load_data()
        regime_result = classifier.classify_regime()
        market_regime = regime_result["regime"]
    except Exception as e:
        print(f"[signals] MarketRegimeClassifier failed: {e}. Falling back to UNCLEAR.")
        market_regime = "UNCLEAR"

    # Maintain some simple breadth stats for logging/display
    stocks_above_ema21 = sum(1 for s in first_pass_results if s.get("price", 0) > s.get("ema21", 0))
    pct_above_ema21 = (stocks_above_ema21 / len(first_pass_results)) * 100 if first_pass_results else 50.0
    nifty_trend_bias = "BULLISH" if pct_above_ema21 > 50 else "BEARISH"

    # 3. Nifty/Market Change Proxy
    nifty_change_proxy = sum(s.get("change_pct", 0.0) for s in first_pass_results) / len(first_pass_results) if first_pass_results else 0.0

    # Query feedback loop statistics from learning engine
    try:
        success_rates = db.get_pattern_success_rates()
        fallback_win_rate = db.get_general_win_rate()
    except Exception:
        success_rates = {}
        fallback_win_rate = 55.0

    sector_groups = {}
    for r in first_pass_results:
        sec = r["sector"]
        if sec not in sector_groups:
            sector_groups[sec] = []
        sector_groups[sec].append(r["_tech_score"] + r["_momentum_score"])

    sector_scores = {}
    for sec, vals in sector_groups.items():
        avg_val = sum(vals) / len(vals)
        sector_scores[sec] = round(avg_val / 2.0, 1)

    # Identify Top 3 Strongest Sectors
    sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
    top_3_sectors = [s[0] for s in sorted_sectors[:3]]

    weights = get_learned_weights()
    results = []
    
    portfolio_state = db.get_portfolio_state()
    active_sector_exposures = portfolio_state.get("sector_exposure", {})
    
    for r in first_pass_results:
        sec = r["sector"]
        sector_score = sector_scores.get(sec, 10.0)

        # Calculate final confidence score (0-100)
        if "_calc_confidence" in r:
            confidence = r["_calc_confidence"]
        else:
            weighted_sum = (
                r["_tech_score"] * weights["technical"]
                + r["_volume_score"] * weights["volume"]
                + sector_score * weights["sector"]
                + r["_momentum_score"] * weights["momentum"]
                + r["_market_score"] * weights["market"]
            )
            max_possible = (
                20 * weights["technical"]
                + 20 * weights["volume"]
                + 20 * weights["sector"]
                + 20 * weights["momentum"]
                + 20 * weights["market"]
            )

            confidence = (
                round((weighted_sum / max_possible) * 100) if max_possible > 0 else 50
            )

        confidence = min(100, max(0, confidence))

        # Sector strength label
        
        # Calculate Current Setup Quality (0-100)
        weighted_sum = (
            r["_tech_score"] * weights["technical"] +
            r["_volume_score"] * weights["volume"] +
            sector_score * weights["sector"] +
            r["_momentum_score"] * weights["momentum"] +
            r["_market_score"] * weights["market"]
        )
        max_possible = (
            20 * weights["technical"] +
            20 * weights["volume"] +
            20 * weights["sector"] +
            20 * weights["momentum"] +
            20 * weights["market"]
        )
        setup_quality = (weighted_sum / max_possible * 100) if max_possible > 0 else 50.0

        # Calculate Relative Strength (RS) vs Nifty
        stock_change = r.get("change_pct", 0.0)
        relative_strength = stock_change - nifty_change_proxy

        # Calculate Sector Strength Label & Confidence Adjustment
        if sector_score >= 14:
            sec_strength = "Strong"
        elif sector_score >= 7:
            sec_strength = "Medium"
        else:
            sec_strength = "Weak"

        # Calculate Market Conditions Score (0-100)
        is_buy_signal = r["score"] > 0
        if market_regime == "TRENDING_BULLISH":
            market_cond_score = 100.0 if is_buy_signal else 0.0
        elif market_regime == "TRENDING_BEARISH":
            market_cond_score = 100.0 if not is_buy_signal else 0.0
        else: # RANGING / VOLATILE
            market_cond_score = 50.0

        # Calculate Pattern Hash & Historical win rate
        vwap_dist = ((r["price"] - r["vwap"]) / r["vwap"] * 100) if r.get("vwap") else 0.0
        pred_dict = {
            "prediction_type": "BULLISH" if is_buy_signal else "BEARISH",
            "rsi": r.get("rsi", 50),
            "macd": r.get("macd_hist", 0),
            "adx": r.get("adx", 20),
            "vwap_distance": vwap_dist,
            "news_score": r.get("news_sentiment", 0.0)
        }
        p_hash = db.get_pattern_hash(pred_dict)
        hist_win_rate = success_rates.get(p_hash, {}).get("win_rate", fallback_win_rate)

        # Refactored Confidence Formula: Strictly Historical
        confidence = round(hist_win_rate)
        confidence = min(100, max(0, confidence))

        # Pricing and PnL expectations
        entry = r["entry"]
        target1 = r["target1"]
        target2 = r["target2"]

        # Expected Move %
        expected_move_pct = round(abs(target1 - entry) / entry * 100, 2)

        # Quantity and expected profit range
        qty = round(capital / entry, 2)

        est_profit_low = round(qty * abs(target1 - entry), 2)
        est_profit_high = round(qty * abs(target2 - entry), 2)
        estimated_profit = f"₹{est_profit_low:.0f} - ₹{est_profit_high:.0f}"

        r["confidence"] = confidence
        r["sector_strength"] = sec_strength
        r["sector_score"] = sector_score
        r["relative_strength"] = round(relative_strength, 2)
        r["market_regime"] = market_regime
        r["nifty_trend"] = nifty_trend_bias
        r["expected_move_pct"] = expected_move_pct
        r["estimated_profit"] = estimated_profit
        
        # Phase Omega: Dynamic Position Sizing
        # Size = Risk Amount / Stop Distance * (Confidence Multiplier) * (PF Multiplier)
        risk_per_share = r.get("risk", 0)
        base_risk_amount = capital * 0.01  # 1% risk per trade limit
        
        # We assume PF multiplier is 1.0 for now unless strategy health says otherwise.
        confidence_multiplier = min(1.0, setup_quality / 100.0)
        total_risk_amount = base_risk_amount * confidence_multiplier
        
        if risk_per_share > 0:
            qty = total_risk_amount / risk_per_share
        else:
            qty = 0
            
        # Enforce max 1% single position risk
        max_investment = capital * 0.20 # E.g. never put more than 20% of capital in one stock
        if (qty * entry) > max_investment:
            qty = max_investment / entry
        
        qty_label = f"{int(qty)} Shares" if qty >= 1 else f"{qty:.2f} Shares"
        
        r["quantity"] = round(qty, 2)
        r["quantity_label"] = qty_label
        r["risk_amount"] = round(total_risk_amount, 2)
        r["confidence_probability"] = round(setup_quality, 2)
        r["market_regime_snapshot"] = market_regime
        
        # Setup Type
        setup_type = "SYSTEM_EDGE"
        if r.get("reasons"):
            setup_type = str(r["reasons"][0]).split('(')[0].strip()
        r["setup_type"] = setup_type.upper().replace(' ', '_')

        # Trade Quality Component Scores (0-100)
        regime_score = market_cond_score
        sector_score_normalized = min(100.0, (sector_score / 20.0) * 100.0)
        vol_score_normalized = min(100.0, (r["_volume_score"] / 20.0) * 100.0)
        rs_score_normalized = min(100.0, max(0.0, 50.0 + (relative_strength * 10.0)))
        news_score_normalized = min(100.0, max(0.0, (r.get("news_sentiment", 0.0) + 100.0) / 2.0))
        correlation_score = 100.0 if active_sector_exposures.get(sec, 0) < 1 else 30.0 # simple correlation proxy
        
        # Weighted Trade Quality Score
        trade_quality_score = (
            regime_score * 0.25 + 
            sector_score_normalized * 0.20 + 
            rs_score_normalized * 0.20 + 
            vol_score_normalized * 0.15 + 
            news_score_normalized * 0.10 + 
            correlation_score * 0.10
        )
        
        r["regime_score"] = round(regime_score, 2)
        r["sector_score"] = round(sector_score_normalized, 2)
        r["volume_score"] = round(vol_score_normalized, 2)
        r["rs_score"] = round(rs_score_normalized, 2)
        r["news_score"] = round(news_score_normalized, 2)
        r["correlation_score"] = round(correlation_score, 2)
        r["trade_quality_score"] = round(trade_quality_score, 2)

        # ── Trade Quality & Capital Management Engine Integration ──
        import trade_quality
        import capital_manager
        
        is_long = r.get("score", 0) >= 0
        tqe_result = trade_quality.TradeQualityEngine.calculate_tqs(
            confidence_score=r.get("confidence", 50),
            is_long=is_long,
            regime=market_regime,
            volatility=r.get("_volume_score", 0),
            volume_expansion=r.get("volume_score", 1.0)
        )
        
        tqs_final = tqe_result["score"]
        classification = tqe_result["classification"]
        
        r["trade_quality_score"] = tqs_final
        r["tqe_classification"] = classification
        
        # Override Base Sizing with CME
        cme_risk_pct = capital_manager.CapitalManagementEngine.calculate_risk_percentage(classification)
        r["cme_risk_pct"] = cme_risk_pct
        
        if cme_risk_pct > 0:
            price = r.get("price", 100)
            stop_loss = r.get("stop_loss", price * 0.99)
            risk_per_share = abs(price - stop_loss) if abs(price - stop_loss) > 0 else (price * 0.01)
            
            base_capital = 100000.0 # Standard unit
            max_loss = base_capital * cme_risk_pct
            qty = max_loss / risk_per_share
            
            r["quantity"] = round(qty, 2)
            r["quantity_label"] = f"{int(qty)} Shares" if qty >= 1 else f"{qty:.2f} Shares"
            r["risk_amount"] = round(max_loss, 2)
        else:
            r["quantity"] = 0
            r["quantity_label"] = "0 Shares (REJECTED)"
            r["risk_amount"] = 0
            r["score"] = 0 # Cancel signal
            
        # ── Define Signal Output ──
        if classification in ["ELITE_CANDIDATE", "INTRADAY_CANDIDATE"]:
            sig = "BUY" if is_long else "SELL"
        elif classification == "WATCHLIST":
            sig = "WEAK BUY" if is_long else "WEAK SELL"
        else:
            sig = "HOLD"
            
        # PHASE 1: Strictly enforce Confidence >= 72
        if r.get("confidence", 50) < 72:
            sig = "HOLD"

        # ── Stock Selection Rules (Phase Omega Strict Filtering) ──
        rejection_reason = None
        rejection_category = None
        
        # 1. Market Trend Alignment
        if is_buy_signal and nifty_trend_bias == "BEARISH":
            sig = "HOLD"
            rejection_category = "MACRO_FILTER"
            rejection_reason = "NIFTY_BEARISH"
            
        # 2. Sector Strength 
        elif sec not in top_3_sectors:
            sig = "HOLD"
            rejection_category = "SECTOR_FILTER"
            rejection_reason = "WEAK_SECTOR"
            
        # 3. Relative Strength
        elif is_buy_signal and relative_strength < 0:
            sig = "HOLD"
            rejection_category = "RS_FILTER"
            rejection_reason = "UNDERPERFORMING_NIFTY"
        elif not is_buy_signal and relative_strength > 0:
            sig = "HOLD"
            rejection_category = "RS_FILTER"
            rejection_reason = "OUTPERFORMING_NIFTY"

        # 4. Market Regime Safety
        elif market_regime == "PANIC" and is_buy_signal:
            sig = "HOLD"
            rejection_category = "REGIME_FILTER"
            rejection_reason = "PANIC_REGIME_NO_LONGS"
        elif market_regime == "RANGING" and (40 < r.get("rsi", 50) < 60):
            sig = "HOLD"
            rejection_category = "REGIME_FILTER"
            rejection_reason = "RANGING_CHOP"

        # 5. Core Validation
        elif r["vol_ratio"] < 1.0 or r["rr_ratio"] < 1.5:
            sig = "HOLD"
            rejection_category = "VALIDATION_FILTER"
            rejection_reason = "LOW_VOLUME_OR_RR"
            
        # 6. Trade Quality Score Cutoff
        elif trade_quality_score < r.get("dynamic_tqs_threshold", 75.0):
            sig = "HOLD"
            rejection_category = "QUALITY_FILTER"
            rejection_reason = f"TQS_BELOW_THRESHOLD_({r.get('dynamic_tqs_threshold', 75.0)})"
            
        # 7. Portfolio Correlation & Sector Exposure Check
        elif active_sector_exposures.get(sec, 0) >= 2: # Max 2 open positions per sector
            sig = "HOLD"
            rejection_category = "PORTFOLIO_LIMIT"
            rejection_reason = "MAX_SECTOR_EXPOSURE_REACHED"

        r["signal"] = sig
        r["direction"] = sig
        
        # Log Rejected Signals into Database for Filter Attribution
        if sig == "HOLD" and rejection_reason:
            r["rejection_category"] = rejection_category
            r["rejection_reason"] = rejection_reason
            r["signal_price"] = r["price"]
            r["target_price"] = r["target1"]
            db.add_rejected_signal(r)

        results.append(r)

    # Sort results
    order = {"BUY": 0, "WEAK BUY": 1, "HOLD": 2, "WEAK SELL": 3, "SELL": 4}
    results.sort(key=lambda x: (order.get(x["signal"], 5), -x["confidence"]))
    return results
