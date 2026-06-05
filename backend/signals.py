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

import math
from datetime import datetime, date, timezone, timedelta
from typing import Optional
import yfinance as yf
import pandas as pd

import numpy as np
import requests

# Browser-like session so Yahoo Finance doesn't block cloud server IPs
_YF_SESSION = requests.Session()
_YF_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})

# Cache for Daily Macro Trend data to speed up intraday scanning
_MACRO_CACHE = {}



# ── Pure pandas/numpy indicator helpers ───────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    line  = _ema(close, fast) - _ema(close, slow)
    sig   = _ema(line, signal)
    hist  = line - sig
    return line, sig, hist

def _bbands(close: pd.Series, period=20, std_dev=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + std_dev * std, mid, mid - std_dev * std  # upper, mid, lower

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean(), tr   # returns (atr, tr)

def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    _, tr  = _atr(high, low, close, period)
    up     = high.diff()
    down   = -low.diff()
    plus_dm  = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr_s    = tr.rolling(period).mean().replace(0, np.nan)
    plus_di  = 100 * plus_dm.rolling(period).mean()  / atr_s
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_s
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.rolling(period).mean()

def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k=14, d=3):
    lo    = low.rolling(k).min()
    hi    = high.rolling(k).max()
    k_pct = 100 * (close - lo) / (hi - lo).replace(0, np.nan)
    return k_pct, k_pct.rolling(d).mean()

def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()

def _vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)

def _supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period=7, multiplier=3.0):
    _, tr = _atr(high, low, close, period)
    atr_s = tr.rolling(period).mean()
    basic_upper = (high + low) / 2 + multiplier * atr_s
    basic_lower = (high + low) / 2 - multiplier * atr_s
    supert     = pd.Series(np.nan, index=close.index)
    supert_dir = pd.Series(1.0,    index=close.index)
    for i in range(1, len(close)):
        bu = basic_upper.iloc[i]
        bl = basic_lower.iloc[i]
        prev = supert.iloc[i - 1] if not np.isnan(supert.iloc[i - 1]) else bl
        pd_  = supert_dir.iloc[i - 1]
        bl   = max(bl, prev) if pd_ == 1 else bl
        bu   = min(bu, prev) if pd_ == -1 else bu
        if close.iloc[i - 1] <= prev:
            supert.iloc[i]     = bu
            supert_dir.iloc[i] = -1
        else:
            supert.iloc[i]     = bl
            supert_dir.iloc[i] = 1
    return supert, supert_dir




# ── NSE Intraday Watchlist ────────────────────────────────────────────────────
NSE_WATCHLIST = [
    {"symbol": "RELIANCE.NS",    "name": "Reliance Industries",  "sector": "Energy"},
    {"symbol": "TCS.NS",         "name": "TCS",                  "sector": "IT"},
    {"symbol": "HDFCBANK.NS",    "name": "HDFC Bank",            "sector": "Banking"},
    {"symbol": "INFY.NS",        "name": "Infosys",              "sector": "IT"},
    {"symbol": "ICICIBANK.NS",   "name": "ICICI Bank",           "sector": "Banking"},
    {"symbol": "KOTAKBANK.NS",   "name": "Kotak Bank",           "sector": "Banking"},
    {"symbol": "SBIN.NS",        "name": "State Bank of India",  "sector": "Banking"},
    {"symbol": "BAJFINANCE.NS",  "name": "Bajaj Finance",        "sector": "Finance"},
    {"symbol": "WIPRO.NS",       "name": "Wipro",                "sector": "IT"},
    {"symbol": "AXISBANK.NS",    "name": "Axis Bank",            "sector": "Banking"},
    {"symbol": "TMPV.NS",        "name": "Tata Motors (TMPV)",   "sector": "Auto"},
    {"symbol": "MARUTI.NS",      "name": "Maruti Suzuki",        "sector": "Auto"},
    {"symbol": "SUNPHARMA.NS",   "name": "Sun Pharma",           "sector": "Pharma"},
    {"symbol": "ADANIENT.NS",    "name": "Adani Enterprises",    "sector": "Conglomerate"},
    {"symbol": "TITAN.NS",       "name": "Titan Company",        "sector": "Consumer"},
    {"symbol": "ULTRACEMCO.NS",  "name": "UltraTech Cement",     "sector": "Cement"},
    {"symbol": "ASIANPAINT.NS",  "name": "Asian Paints",         "sector": "Consumer"},
    {"symbol": "HINDUNILVR.NS",  "name": "Hindustan Unilever",   "sector": "FMCG"},
    {"symbol": "ONGC.NS",        "name": "ONGC",                 "sector": "Energy"},
    {"symbol": "NTPC.NS",        "name": "NTPC",                 "sector": "Power"},
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


def _download_market_data(symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    """
    Downloads market data with fallback handling.
    This serves as the primary data abstraction layer.
    
    To migrate to a dedicated broker API (like Zerodha Kite Connect, Dhan, Upstox, or TrueData):
    1. Initialize the broker client session (e.g. kite = KiteConnect(api_key=...)).
    2. Replace the yfinance logic below with your broker API historical data call:
       e.g., records = kite.historical_data(instrument_token, from_date, to_date, interval)
       df = pd.DataFrame(records)
    3. Ensure standard columns ['Open', 'High', 'Low', 'Close', 'Volume'] are returned
       with a datetime index.
    """
    try:
        df = yf.download(
            symbol, period=period, interval=interval,
            auto_adjust=True, progress=False,
            session=_YF_SESSION,
        )
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"[Data Abstraction] Error downloading {symbol} ({interval}): {e}")
    return None


# ── Core Signal Calculation ───────────────────────────────────────────────────

def analyse_symbol(symbol: str, name: str, sector: str) -> Optional[dict]:
    """
    Download market data for a symbol and calculate advanced signals using pandas-ta.
    If market is open, runs intraday 5m scan.
    If market is closed, runs daily 1d overnight scan.
    """
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
            _MACRO_CACHE[symbol] = {
                "date": current_date_str,
                "bullish": macro_bullish
            }

        if df is None or len(df) < 20:
            return None

        # Flatten multi-level columns if returned by yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close", "High", "Low", "Open", "Volume"])
        if len(df) < 20:
            return None

        # ── Pure pandas/numpy indicators (no pandas-ta dependency) ────────
        close  = df["Close"]
        high   = df["High"]
        low    = df["Low"]
        volume = df["Volume"]

        # EMA
        df["EMA_9"]  = close.ewm(span=9,  adjust=False).mean()
        df["EMA_21"] = close.ewm(span=21, adjust=False).mean()

        # RSI(14)
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        df["RSI_14"] = 100 - (100 / (1 + rs))

        # MACD(12,26,9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["MACD_12_26_9"]  = ema12 - ema26
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
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)
        df["ATRr_14"] = tr.rolling(14).mean()

        # Supertrend(7, 3.0)
        atr7 = tr.rolling(7).mean()
        basic_upper = (high + low) / 2 + 3.0 * atr7
        basic_lower = (high + low) / 2 - 3.0 * atr7
        supert = pd.Series(np.nan, index=df.index)
        supert_dir_s = pd.Series(1.0, index=df.index)
        for i in range(1, len(df)):
            prev_close = close.iloc[i - 1]
            bu = basic_upper.iloc[i]
            bl = basic_lower.iloc[i]
            prev_supert = supert.iloc[i - 1] if not np.isnan(supert.iloc[i - 1]) else bl
            prev_dir    = supert_dir_s.iloc[i - 1]
            if prev_dir == 1:
                bl = max(bl, prev_supert)
            else:
                bu = min(bu, prev_supert)
            if prev_close <= prev_supert:
                supert.iloc[i] = bu
                supert_dir_s.iloc[i] = -1
            else:
                supert.iloc[i] = bl
                supert_dir_s.iloc[i] = 1
        df["SUPERT_7_3.0"]  = supert
        df["SUPERTd_7_3.0"] = supert_dir_s

        # ADX(14)
        up_move   = high.diff()
        down_move = -low.diff()
        plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        atr14     = df["ATRr_14"]
        plus_di   = 100 * pd.Series(plus_dm,  index=df.index).rolling(14).mean() / atr14.replace(0, np.nan)
        minus_di  = 100 * pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14.replace(0, np.nan)
        dx        = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        df["ADX_14"] = dx.rolling(14).mean()

        # Stochastic(14,3,3)
        low14  = low.rolling(14).min()
        high14 = high.rolling(14).max()
        df["STOCHk_14_3_3"] = 100 * (close - low14) / (high14 - low14).replace(0, np.nan)
        df["STOCHd_14_3_3"] = df["STOCHk_14_3_3"].rolling(3).mean()

        # OBV
        obv = [0]
        for i in range(1, len(df)):
            if close.iloc[i] > close.iloc[i - 1]:
                obv.append(obv[-1] + volume.iloc[i])
            elif close.iloc[i] < close.iloc[i - 1]:
                obv.append(obv[-1] - volume.iloc[i])
            else:
                obv.append(obv[-1])
        df["OBV"] = obv

        # Drop rows with NaN in key columns
        required_cols = [
            "Close", "EMA_9", "EMA_21", "RSI_14", "MACD_12_26_9",
            "BBU_20_2.0", "VWAP_D", "ATRr_14", "SUPERT_7_3.0",
            "ADX_14", "STOCHk_14_3_3", "OBV"
        ]
        df = df.dropna(subset=required_cols)
        if len(df) < 5:
            return None

        # Extract latest indicator values
        price      = float(close.iloc[-1])
        rsi_val    = float(df["RSI_14"].iloc[-1])
        macd_val   = float(df["MACD_12_26_9"].iloc[-1])
        sig_val    = float(df["MACDs_12_26_9"].iloc[-1])
        hist_val   = float(df["MACDh_12_26_9"].iloc[-1])
        hist_prev  = float(df["MACDh_12_26_9"].iloc[-2])
        ema9_val   = float(df["EMA_9"].iloc[-1])
        ema21_val  = float(df["EMA_21"].iloc[-1])
        vwap_val   = float(df["VWAP_D"].iloc[-1])
        bb_up      = float(df["BBU_20_2.0"].iloc[-1])
        bb_lo      = float(df["BBL_20_2.0"].iloc[-1])
        bb_mid_v   = float(df["BBM_20_2.0"].iloc[-1])
        atr_val    = float(df["ATRr_14"].iloc[-1])
        
        # New indicators
        supert_val = float(df["SUPERT_7_3.0"].iloc[-1])
        supert_dir = float(df["SUPERTd_7_3.0"].iloc[-1])
        adx_val    = float(df["ADX_14"].iloc[-1])
        stoch_k    = float(df["STOCHk_14_3_3"].iloc[-1])
        stoch_d    = float(df["STOCHd_14_3_3"].iloc[-1])
        obv_val    = float(df["OBV"].iloc[-1])
        obv_prev   = float(df["OBV"].iloc[-5])

        # Volume ratio vs 20-bar average
        vol_avg  = volume.rolling(20).mean()
        vol_ratio = (volume / vol_avg.replace(0, 1)).iloc[-1]
        vol_r     = float(vol_ratio)

        # ── Scoring system (Bullish: positive, Bearish: negative) ─────────────
        score = 0
        reasons_bull = []
        reasons_bear = []

        # 1. VWAP position (strong weight for intraday)
        vwap_diff_pct = (price - vwap_val) / vwap_val * 100
        if price > vwap_val * 1.002:
            score += 2
            reasons_bull.append(f"Price {abs(vwap_diff_pct):.1f}% above VWAP ₹{vwap_val:.1f}")
        elif price < vwap_val * 0.998:
            score -= 2
            reasons_bear.append(f"Price {abs(vwap_diff_pct):.1f}% below VWAP ₹{vwap_val:.1f}")

        # 2. RSI Overbought/Oversold
        if 45 <= rsi_val <= 65:
            score += 1
            reasons_bull.append(f"RSI {rsi_val:.0f} — stable bullish momentum")
        elif rsi_val > 70:
            score -= 2
            reasons_bear.append(f"RSI {rsi_val:.0f} — overbought risk")
        elif rsi_val < 35:
            score += 2
            reasons_bull.append(f"RSI {rsi_val:.0f} — oversold bounce candidate")
        elif rsi_val < 45:
            score -= 1
            reasons_bear.append(f"RSI {rsi_val:.0f} — weak price momentum")

        # 3. MACD Histogram and Signal Line Crossover
        if hist_val > 0 and hist_val > hist_prev:
            score += 2
            reasons_bull.append("MACD histogram expanding bullishly")
        elif hist_val < 0 and hist_val < hist_prev:
            score -= 2
            reasons_bear.append("MACD histogram expanding bearishly")

        if macd_val > sig_val and df["MACD_12_26_9"].iloc[-2] <= df["MACDs_12_26_9"].iloc[-2]:
            score += 2
            reasons_bull.append("MACD bullish crossover")
        elif macd_val < sig_val and df["MACD_12_26_9"].iloc[-2] >= df["MACDs_12_26_9"].iloc[-2]:
            score -= 2
            reasons_bear.append("MACD bearish crossover")

        # 4. EMA 9/21 Trend Structure
        if ema9_val > ema21_val:
            score += 1
            reasons_bull.append("Uptrend (EMA 9 > EMA 21)")
        else:
            score -= 1
            reasons_bear.append("Downtrend (EMA 9 < EMA 21)")

        # 5. Bollinger Bands
        pct_b = (price - bb_lo) / (bb_up - bb_lo) if (bb_up - bb_lo) > 0 else 0.5
        if pct_b > 0.85:
            score -= 1
            reasons_bear.append(f"Price near upper BBand (B% {pct_b:.0%})")
        elif pct_b < 0.15:
            score += 1
            reasons_bull.append(f"Price near lower BBand (B% {pct_b:.0%})")

        # 6. Supertrend (Strong Weight)
        if supert_dir == 1:
            score += 2
            reasons_bull.append("Supertrend Bullish")
        else:
            score -= 2
            reasons_bear.append("Supertrend Bearish")

        # 7. ADX Trend Strength Modifier
        if adx_val > 40:
            if score > 0:
                score += 2
                reasons_bull.append(f"Very Strong Trend (ADX {adx_val:.1f})")
            elif score < 0:
                score -= 2
                reasons_bear.append(f"Very Strong Trend (ADX {adx_val:.1f})")
        elif adx_val > 25:
            if score > 0:
                score += 1
                reasons_bull.append(f"Strong Trend (ADX {adx_val:.1f})")
            elif score < 0:
                score -= 1
                reasons_bear.append(f"Strong Trend (ADX {adx_val:.1f})")
        elif adx_val < 15:
            score = 0  # completely skip signal
            reasons_bear.append(f"Choppy sideways market (ADX {adx_val:.1f} < 15)")
            reasons_bull.append(f"Choppy sideways market (ADX {adx_val:.1f} < 15)")
        elif adx_val < 20:
            score = int(score * 0.7)  # 30% penalty
            reasons_bear.append(f"Weak sideways market (ADX {adx_val:.1f} < 20)")

        # 7.5 Macro Trend Alignment (Multi-Timeframe Analysis)
        if macro_bullish is not None:
            if macro_bullish:
                if score > 0:
                    score += 3
                    reasons_bull.insert(0, "Macro Trend Aligned (Daily Bullish)")
                elif score < 0:
                    score += 1 # Cushion the drop
                    reasons_bear.append("Counter-trend Intraday (Macro is Bullish)")
            else:
                if score < 0:
                    score -= 3
                    reasons_bear.insert(0, "Macro Trend Aligned (Daily Bearish)")
                elif score > 0:
                    score -= 2 # Penalize intraday buy in daily downtrend
                    reasons_bull.append("Counter-trend Intraday (Macro is Bearish)")

        # 8. Stochastic Crossovers
        if stoch_k < 20 and stoch_k > stoch_d and df["STOCHk_14_3_3"].iloc[-2] <= df["STOCHd_14_3_3"].iloc[-2]:
            score += 1
            reasons_bull.append("Stochastic oversold golden cross")
        elif stoch_k > 80 and stoch_k < stoch_d and df["STOCHk_14_3_3"].iloc[-2] >= df["STOCHd_14_3_3"].iloc[-2]:
            score -= 1
            reasons_bear.append("Stochastic overbought death cross")

        # 9. OBV Volume Flow
        if obv_val > obv_prev:
            score += 1
            reasons_bull.append("OBV volume accumulation")
        elif obv_val < obv_prev:
            score -= 1
            reasons_bear.append("OBV volume distribution")

        # 9.5 Candlestick Pattern Recognition (Based on Candlestick Bible)
        try:
            # Check latest bar details
            latest_open  = float(df["Open"].iloc[-1])
            latest_high  = float(df["High"].iloc[-1])
            latest_low   = float(df["Low"].iloc[-1])
            latest_close = float(df["Close"].iloc[-1])
            prev_open    = float(df["Open"].iloc[-2])
            prev_close   = float(df["Close"].iloc[-2])
            
            body = abs(latest_close - latest_open)
            candle_range = (latest_high - latest_low) if (latest_high - latest_low) > 0 else 0.001
            upper_wick = (latest_high - max(latest_open, latest_close))
            lower_wick = (min(latest_open, latest_close) - latest_low)
            
            # 1. Hammer (Bullish reversal pattern)
            # Body is small, lower wick is at least 2x body size, little to no upper wick
            if lower_wick > (2 * body) and upper_wick < (0.1 * candle_range) and body > (0.05 * candle_range):
                if vol_r >= 1.5:
                    score += 3
                    reasons_bull.append(f"Candlestick: Bullish Hammer detected (vol surge {vol_r:.1f}x)")
                else:
                    reasons_bull.append(f"Candlestick: Hammer detected but rejected (low volume {vol_r:.1f}x)")
                
            # 2. Shooting Star (Bearish reversal pattern)
            # Body is small, upper wick is at least 2x body size, little to no lower wick
            elif upper_wick > (2 * body) and lower_wick < (0.1 * candle_range) and body > (0.05 * candle_range):
                if vol_r >= 1.5:
                    score -= 3
                    reasons_bear.append(f"Candlestick: Bearish Shooting Star detected (vol surge {vol_r:.1f}x)")
                else:
                    reasons_bear.append(f"Candlestick: Shooting Star rejected (low volume {vol_r:.1f}x)")
                
            # 3. Engulfing Patterns
            else:
                # Bullish Engulfing: previous candle was bearish, current candle is bullish and its body fully engulfs the previous body
                if latest_close > latest_open and prev_close < prev_open:
                    if latest_close >= prev_open and latest_open <= prev_close:
                        if vol_r >= 1.5:
                            score += 3
                            reasons_bull.append(f"Candlestick: Bullish Engulfing pattern (vol surge {vol_r:.1f}x)")
                        else:
                            reasons_bull.append(f"Candlestick: Engulfing pattern rejected (low volume {vol_r:.1f}x)")
                # Bearish Engulfing: previous candle was bullish, current candle is bearish and its body fully engulfs the previous body
                elif latest_close < latest_open and prev_close > prev_open:
                    if latest_close <= prev_open and latest_open >= prev_close:
                        if vol_r >= 1.5:
                            score -= 3
                            reasons_bear.append(f"Candlestick: Bearish Engulfing pattern (vol surge {vol_r:.1f}x)")
                        else:
                            reasons_bear.append(f"Candlestick: Engulfing pattern rejected (low volume {vol_r:.1f}x)")
                        
            # 4. Marubozu (Strong momentum indicator)
            # Body represents >90% of the entire range
            if body / candle_range > 0.90:
                if latest_close > latest_open:
                    if vol_r >= 1.5:
                        score += 2
                        reasons_bull.append(f"Candlestick: Bullish Marubozu (Extreme buying force, vol surge {vol_r:.1f}x)")
                    else:
                        reasons_bull.append(f"Candlestick: Bullish Marubozu rejected (low volume {vol_r:.1f}x)")
                else:
                    if vol_r >= 1.5:
                        score -= 2
                        reasons_bear.append(f"Candlestick: Bearish Marubozu (Extreme selling force, vol surge {vol_r:.1f}x)")
                    else:
                        reasons_bear.append(f"Candlestick: Bearish Marubozu rejected (low volume {vol_r:.1f}x)")
        except Exception:
            pass

        # 10. Volume Confirmation
        if vol_r >= 1.5:
            score += 1 if score > 0 else -1
            label = "bull" if score > 0 else "bear"
            reasons_bull.append(f"Vol surge {vol_r:.1f}x — {label} force") if score > 0 else \
            reasons_bear.append(f"Vol surge {vol_r:.1f}x — {label} force")
        elif vol_r < 0.7:
            score = int(score * 0.7)
            reasons_bear.append("Low volume conviction")

        # ── Define Signal Output ──────────────────────────────────────────────
        if score >= 7:
            signal    = "BUY"
            confidence = min(95, 60 + score * 3)
        elif score <= -7:
            signal    = "SELL"
            confidence = min(95, 60 + abs(score) * 3)
        elif score >= 4:
            signal    = "WEAK BUY"
            confidence = 40 + score * 4
        elif score <= -4:
            signal    = "WEAK SELL"
            confidence = 40 + abs(score) * 4
        else:
            signal    = "HOLD"
            confidence = 50

        # 11. Volatility Clustering Boost
        atr_pct = (atr_val / price) * 100
        if atr_pct > 2.5 and vol_r > 1.8:
            confidence = min(95, confidence * 1.3)
            if score > 0:
                reasons_bull.insert(0, f"Volatility Clustering Boost (ATR% {atr_pct:.1f})")
            elif score < 0:
                reasons_bear.insert(0, f"Volatility Clustering Boost (ATR% {atr_pct:.1f})")

        # ── Set Target & Stop Levels via ATR & Macro Alignment ────────────────
        is_trend_following = (signal in ("BUY", "WEAK BUY") and macro_bullish) or (signal in ("SELL", "WEAK SELL") and macro_bullish is False)
        
        atr_target_mult = 2.0 if is_trend_following else 1.5
        atr_stop_mult = 3.0 if is_trend_following else 2.5
        
        atr_target = atr_val * atr_target_mult
        atr_stop = atr_val * atr_stop_mult

        if signal in ("BUY", "WEAK BUY"):
            entry  = round(price, 2)
            target = round(price + atr_target, 2)
            stop   = round(price - atr_stop, 2)
            risk   = round(price - stop, 2)
            reward = round(target - price, 2)
        elif signal in ("SELL", "WEAK SELL"):
            entry  = round(price, 2)
            target = round(price - atr_target, 2)
            stop   = round(price + atr_stop, 2)
            risk   = round(stop - price, 2)
            reward = round(price - target, 2)
        else:
            entry  = round(price, 2)
            target = round(price + atr_val, 2)
            stop   = round(price - atr_val, 2)
            risk   = round(atr_val, 2)
            reward = round(atr_val, 2)

        rr_ratio = round(reward / risk, 2) if risk > 0 else 1.0
        target_pct = round((target - price) / price * 100, 2)

        # reasoning output (join top 4 signals)
        all_reasons = reasons_bull + reasons_bear
        reasoning = " | ".join(all_reasons[:4])

        return {
            "symbol":       symbol,
            "name":         name,
            "sector":       sector,
            "signal":       signal,
            "confidence":   round(confidence),
            "score":        score,
            "price":        entry,
            "entry":        entry,
            "target":       target,
            "stop_loss":    stop,
            "target_pct":   target_pct,
            "risk":         risk,
            "reward":       reward,
            "rr_ratio":     rr_ratio,
            "rsi":          round(rsi_val, 1),
            "macd_hist":    round(hist_val, 4),
            "vwap":         round(vwap_val, 2),
            "ema9":         round(ema9_val, 2),
            "ema21":        round(ema21_val, 2),
            "bb_upper":     round(bb_up, 2),
            "bb_lower":     round(bb_lo, 2),
            "vol_ratio":    round(vol_r, 2),
            "atr":          round(atr_val, 2),
            "supertrend":   round(supert_val, 2),
            "supertrend_dir": int(supert_dir),
            "adx":          round(adx_val, 2),
            "stoch_k":      round(stoch_k, 2),
            "obv":          round(obv_val, 2),
            "scan_type":    scan_type,
            "reasoning":    reasoning,
            "reasons":      all_reasons,
            "scanned_at":   datetime.utcnow().isoformat() + "Z",
        }

    except Exception:
        return None


def run_scan(symbols: Optional[list] = None) -> list:
    """
    Scan watchlist and return signals sorted by conviction/confidence.
    """
    from concurrent.futures import ThreadPoolExecutor
    watchlist = symbols or NSE_WATCHLIST
    results = []

    def worker(item):
        return analyse_symbol(item["symbol"], item["name"], item["sector"])

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, item) for item in watchlist]
        for fut in futures:
            try:
                sig = fut.result()
                if sig:
                    results.append(sig)
            except Exception:
                pass

    order = {"BUY": 0, "WEAK BUY": 1, "HOLD": 2, "WEAK SELL": 3, "SELL": 4}
    results.sort(key=lambda x: (order.get(x["signal"], 5), -x["confidence"]))
    return results
