"""
signals.py — NSE Intraday Signal Engine
────────────────────────────────────────────────────────────────────────────────
Real quantitative analysis using:
  • VWAP          — intraday anchor (most important for NSE intraday)
  • RSI(14)       — momentum overbought/oversold
  • MACD(12,26,9) — trend + momentum crossover
  • EMA 9 / 21   — intraday fast/slow moving averages
  • Bollinger Bands(20,2) — volatility squeeze / expansion
  • Volume ratio  — current volume vs 20-bar average

Signal scoring: each condition adds/subtracts from a score.
Score →  BUY/SELL/HOLD + Confidence %
"""

import math
from datetime import datetime, date
from typing import Optional
import yfinance as yf
import pandas as pd


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


# ── Technical Indicator Functions ─────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast   = _ema(series, fast)
    ema_slow   = _ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(series: pd.Series, period=20, std_dev=2):
    sma    = series.rolling(period).mean()
    std    = series.rolling(period).std()
    upper  = sma + std_dev * std
    lower  = sma - std_dev * std
    return upper, sma, lower


def _vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP = cumulative(typical_price * volume) / cumulative(volume)"""
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_vol  = df["Volume"].cumsum()
    cum_tp_vol = (typical * df["Volume"]).cumsum()
    return cum_tp_vol / cum_vol.replace(0, 1)


def _atr(df: pd.DataFrame, period=14) -> pd.Series:
    """Average True Range for stop-loss calculation."""
    high, low, prev_close = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ── Core Signal Calculation ───────────────────────────────────────────────────

def analyse_symbol(symbol: str, name: str, sector: str) -> Optional[dict]:
    """
    Fetch 5-minute intraday data for today and compute a full signal.
    Returns a dict or None if data unavailable.
    """
    try:
        # Fetch 5-min data for the past 5 days (ensures data is always available, e.g. on weekends)
        df = yf.download(symbol, period="5d", interval="5m",
                         auto_adjust=True, progress=False)
        if df is None or len(df) < 20:
            return None

        # Flatten multi-level columns (yfinance sometimes returns them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()
        if len(df) < 20:
            return None

        # ── Indicators ───────────────────────────────────────────────────────
        close  = df["Close"]
        volume = df["Volume"]

        ema9  = _ema(close, 9)
        ema21 = _ema(close, 21)
        rsi   = _rsi(close, 14)
        macd_line, signal_line, macd_hist = _macd(close)
        bb_upper, bb_mid, bb_lower = _bollinger(close, 20, 2)
        vwap  = _vwap(df)
        atr   = _atr(df, 14)

        # Volume: current bar vs 20-bar rolling average
        vol_avg  = volume.rolling(20).mean()
        vol_ratio = (volume / vol_avg.replace(0, 1)).iloc[-1]

        # ── Latest values ─────────────────────────────────────────────────────
        price     = float(close.iloc[-1])
        rsi_val   = float(rsi.iloc[-1])
        macd_val  = float(macd_line.iloc[-1])
        sig_val   = float(signal_line.iloc[-1])
        hist_val  = float(macd_hist.iloc[-1])
        hist_prev = float(macd_hist.iloc[-2]) if len(macd_hist) > 1 else 0
        ema9_val  = float(ema9.iloc[-1])
        ema21_val = float(ema21.iloc[-1])
        vwap_val  = float(vwap.iloc[-1])
        bb_up     = float(bb_upper.iloc[-1])
        bb_lo     = float(bb_lower.iloc[-1])
        bb_mid_v  = float(bb_mid.iloc[-1])
        atr_val   = float(atr.iloc[-1])
        vol_r     = float(vol_ratio)

        # ── Scoring system (bullish = positive, bearish = negative) ───────────
        score = 0
        reasons_bull = []
        reasons_bear = []

        # 1. VWAP: price vs VWAP (strong intraday signal)
        vwap_diff_pct = (price - vwap_val) / vwap_val * 100
        if price > vwap_val * 1.002:
            score += 2
            reasons_bull.append(f"Price {abs(vwap_diff_pct):.1f}% above VWAP ₹{vwap_val:.1f} — bullish bias")
        elif price < vwap_val * 0.998:
            score -= 2
            reasons_bear.append(f"Price {abs(vwap_diff_pct):.1f}% below VWAP ₹{vwap_val:.1f} — bearish bias")

        # 2. RSI momentum
        if 45 <= rsi_val <= 65:
            score += 1
            reasons_bull.append(f"RSI {rsi_val:.0f} — healthy bullish momentum (not overbought)")
        elif rsi_val > 70:
            score -= 2
            reasons_bear.append(f"RSI {rsi_val:.0f} — overbought, risk of reversal")
        elif rsi_val < 35:
            score += 1   # oversold bounce potential
            reasons_bull.append(f"RSI {rsi_val:.0f} — oversold, watch for bounce")
        elif rsi_val < 45:
            score -= 1
            reasons_bear.append(f"RSI {rsi_val:.0f} — weak momentum")

        # 3. MACD — histogram expanding bullish/bearish
        if hist_val > 0 and hist_val > hist_prev:
            score += 2
            reasons_bull.append(f"MACD histogram expanding bullishly ({hist_val:.3f})")
        elif hist_val > 0 and hist_val < hist_prev:
            score += 0  # losing steam
        elif hist_val < 0 and hist_val < hist_prev:
            score -= 2
            reasons_bear.append(f"MACD histogram expanding bearishly ({hist_val:.3f})")
        elif hist_val < 0 and hist_val > hist_prev:
            score -= 0  # bear losing steam

        # MACD crossover (recent: current bar crosses signal)
        if macd_val > sig_val and macd_line.iloc[-2] <= signal_line.iloc[-2]:
            score += 2
            reasons_bull.append("MACD bullish crossover just occurred — momentum shift")
        elif macd_val < sig_val and macd_line.iloc[-2] >= signal_line.iloc[-2]:
            score -= 2
            reasons_bear.append("MACD bearish crossover just occurred — momentum shift")

        # 4. EMA 9 vs EMA 21 alignment
        if ema9_val > ema21_val:
            score += 1
            reasons_bull.append(f"EMA9 ({ema9_val:.1f}) > EMA21 ({ema21_val:.1f}) — uptrend structure")
        else:
            score -= 1
            reasons_bear.append(f"EMA9 ({ema9_val:.1f}) < EMA21 ({ema21_val:.1f}) — downtrend structure")

        # 5. Bollinger Band position
        bb_width = (bb_up - bb_lo) / bb_mid_v * 100  # %
        pct_b    = (price - bb_lo) / (bb_up - bb_lo) if (bb_up - bb_lo) > 0 else 0.5
        if pct_b > 0.8:
            score -= 1
            reasons_bear.append(f"Near upper Bollinger Band (B% {pct_b:.0%}) — stretched")
        elif pct_b < 0.2:
            score += 1
            reasons_bull.append(f"Near lower Bollinger Band (B% {pct_b:.0%}) — potential bounce")

        # 6. Volume confirmation
        if vol_r >= 1.5:
            score += 1 if score > 0 else -1   # amplifies the existing direction
            label = "bull" if score > 0 else "bear"
            reasons_bull.append(f"Volume {vol_r:.1f}x average — strong {label} confirmation") if score > 0 else \
            reasons_bear.append(f"Volume {vol_r:.1f}x average — strong {label} confirmation")
        elif vol_r < 0.7:
            score = int(score * 0.7)  # low volume = lower conviction
            reasons_bear.append(f"Volume {vol_r:.1f}x average — low conviction, avoid")

        # ── Determine signal ──────────────────────────────────────────────────
        max_score = 11  # theoretical maximum
        norm      = score / max_score  # -1 to +1

        if score >= 4:
            signal    = "BUY"
            confidence = min(95, 60 + score * 4)
        elif score <= -4:
            signal    = "SELL"
            confidence = min(95, 60 + abs(score) * 4)
        elif score >= 2:
            signal    = "WEAK BUY"
            confidence = 40 + score * 5
        elif score <= -2:
            signal    = "WEAK SELL"
            confidence = 40 + abs(score) * 5
        else:
            signal    = "HOLD"
            confidence = 50

        # ── Price targets using ATR ───────────────────────────────────────────
        atr2 = atr_val * 2   # 2×ATR for target
        atr1 = atr_val * 1.2  # 1.2×ATR for stop

        if signal in ("BUY", "WEAK BUY"):
            entry  = round(price, 2)
            target = round(price + atr2, 2)
            stop   = round(price - atr1, 2)
            risk   = round(price - stop, 2)
            reward = round(target - price, 2)
        elif signal in ("SELL", "WEAK SELL"):
            entry  = round(price, 2)
            target = round(price - atr2, 2)
            stop   = round(price + atr1, 2)
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

        # Build reasoning string
        all_reasons = reasons_bull + reasons_bear
        reasoning = " | ".join(all_reasons[:4])  # top 4 reasons

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
            "reasoning":    reasoning,
            "scanned_at":   datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        return None


def run_scan(symbols: Optional[list] = None) -> list:
    """
    Scan all NSE symbols (or a subset) and return signals sorted by confidence.
    Uses ThreadPoolExecutor to download and analyze symbols concurrently.
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

    # Sort: BUY first by confidence, then SELL by confidence, then HOLD
    order = {"BUY": 0, "WEAK BUY": 1, "HOLD": 2, "WEAK SELL": 3, "SELL": 4}
    results.sort(key=lambda x: (order.get(x["signal"], 5), -x["confidence"]))
    return results
