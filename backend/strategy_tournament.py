"""
backend/strategy_tournament.py — 30-Strategy Quant Tournament Engine for ApexTrade AI
Runs 30 distinct quantitative trading strategies across all local historical datasets
(legacy 10-year CSVs merged with the new 7-year daily_7y set), with a walk-forward
calibration: strategies select params on the 2019-2023 in-sample slice and are
re-scored unmodified on the 2024-2026 out-of-sample slice.
"""
import os
import sys
import math
import numpy as np
import pandas as pd
from collections import Counter
from typing import Dict, List, Any, Tuple

backend_dir = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_DATA_DIR = os.path.join(backend_dir, "historical_data")
DAILY_7Y_DIRNAME = "daily_7y"

# Walk-forward mandate: In-Sample = 2019-2023, Out-of-Sample = 2024-2026
IS_END_YEAR = 2023
IS_WEIGHT = 0.40
OOS_WEIGHT = 0.60

try:
    from quant.cost_engine import CostEngine
except ImportError:  # pragma: no cover - direct script execution
    sys.path.insert(0, backend_dir)
    from quant.cost_engine import CostEngine

SIDE_COST_BPS = CostEngine.DEFAULT_SIDE_COST_BPS

STRATEGY_REGISTRY = {
    # Bucket 1: Trend Following / Momentum (1-6)
    1: {"name": "SMA Dual Cross (20/50)", "bucket": "Trend Following"},
    2: {"name": "EMA Fast Momentum (9/21)", "bucket": "Trend Following"},
    3: {"name": "Triple MA System (10/20/50)", "bucket": "Trend Following"},
    4: {"name": "SuperTrend Quant (10, 3.0)", "bucket": "Trend Following"},
    5: {"name": "Parabolic SAR Acceleration", "bucket": "Trend Following"},
    6: {"name": "KAMA Adaptive Moving Average", "bucket": "Trend Following"},

    # Bucket 2: Mean Reversion / Oscillators (7-12)
    7: {"name": "RSI Reversion (30/70)", "bucket": "Mean Reversion"},
    8: {"name": "RSI Bull/Bear Divergence", "bucket": "Mean Reversion"},
    9: {"name": "Stochastic Oscillator (%K/%D)", "bucket": "Mean Reversion"},
    10: {"name": "Bollinger Bands Bounce (20, 2.0)", "bucket": "Mean Reversion"},
    11: {"name": "Williams %R Reversal (-80/-20)", "bucket": "Mean Reversion"},
    12: {"name": "Commodity Channel Index (CCI 20)", "bucket": "Mean Reversion"},

    # Bucket 3: Breakout & Volatility Expansion (13-18)
    13: {"name": "Donchian Channel Breakout (20-Day)", "bucket": "Breakout"},
    14: {"name": "Keltner Channel Squeeze", "bucket": "Breakout"},
    15: {"name": "ATR Trailing Stop Breakout (2.5x ATR)", "bucket": "Breakout"},
    16: {"name": "Bollinger Squeeze Expansion", "bucket": "Breakout"},
    17: {"name": "High Volume Surge Breakout (>2.0x Vol)", "bucket": "Breakout"},
    18: {"name": "52-Week High Momentum Breakout", "bucket": "Breakout"},

    # Bucket 4: Volume & Order Flow Dynamics (19-24)
    19: {"name": "VWAP Dynamic Reversion (20-period)", "bucket": "Volume Dynamics"},
    20: {"name": "On-Balance Volume (OBV) Trend", "bucket": "Volume Dynamics"},
    21: {"name": "Money Flow Index (MFI 14 Reversals)", "bucket": "Volume Dynamics"},
    22: {"name": "Chaikin Money Flow (CMF 20 > 0.15)", "bucket": "Volume Dynamics"},
    23: {"name": "Volume Price Trend (VPT) Divergence", "bucket": "Volume Dynamics"},
    24: {"name": "Accumulation / Distribution Spike", "bucket": "Volume Dynamics"},

    # Bucket 5: Multi-Factor & Regime-Adaptive (25-32)
    25: {"name": "MACD + RSI Confluence", "bucket": "Multi-Factor"},
    26: {"name": "ADX Trend Strength Filter (ADX > 25)", "bucket": "Multi-Factor"},
    27: {"name": "Sharpe Rank Volatility Sizing", "bucket": "Multi-Factor"},
    28: {"name": "Multi-Timeframe Trend Confirmation", "bucket": "Multi-Factor"},
    29: {"name": "Ichimoku Cloud Kumo Breakout", "bucket": "Multi-Factor"},
    30: {"name": "Apex Regime-Adaptive Quant Strategy", "bucket": "Multi-Factor"},
    31: {"name": "Volatility-Targeted Momentum (12% Vol Target)", "bucket": "Multi-Factor"},
    32: {"name": "Gap & Go Breakaway Momentum", "bucket": "Breakout"},
}

# ── Calibration grids (walk-forward parameter variants) ──────────────────────
# Chosen by best in-sample Sharpe, then validated on out-of-sample data.
# All grids come from the user's calibration directive:
#   - SuperTrend: ATR length 10 vs 14, multiplier 2.5 vs 3.0
#   - Bollinger bounce: band std 2.0 vs 2.5, both with RSI 30/70 extremity gates
#   - Volume-surge breakout: 1.5x / 2.0x / 2.5x of 20-bar average volume
PARAM_GRID: Dict[int, List[Dict[str, Any]]] = {
    4: [
        {"atr_len": 10, "mult": 3.0},
        {"atr_len": 10, "mult": 2.5},
        {"atr_len": 14, "mult": 3.0},
        {"atr_len": 14, "mult": 2.5},
    ],
    10: [
        {"bb_std": 2.0},
        {"bb_std": 2.5},
    ],
    17: [
        {"vol_mult": 1.5},
        {"vol_mult": 2.0},
        {"vol_mult": 2.5},
    ],
}


def get_param_grid(strat_id: int) -> List[Dict[str, Any]]:
    """Parameter candidates for a strategy; [{}] = non-parametric."""
    return PARAM_GRID.get(strat_id, [{}])


# ── Dataset loading (legacy 10y + new 7y daily exports) ──────────────────────

_INDEX_ALIASES = {
    "INDEX_NSEI": "NIFTY_50_INDEX",
    "INDEX_NSEBANK": "BANK_NIFTY_INDEX",
}


def _instrument_key(path: str) -> str:
    """Normalize a dataset filename to a stable instrument key."""
    stem = os.path.splitext(os.path.basename(path))[0]
    for suffix in ("_10y_daily", "_7y_daily"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return _INDEX_ALIASES.get(stem, stem.upper())


def _load_dataset_frame(path: str) -> pd.DataFrame:
    """Load a CSV (DatetimeIndex first col) or parquet (Date column) dataset.

    Normalizes headers to OHLCV expectations and drops dividend/split metadata
    columns produced by the yfinance-parquet export.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".parquet":
        df = pd.read_parquet(path)
        date_col = next((c for c in df.columns if str(c).lower() == "date"), None)
        if date_col is not None:
            df = df.set_index(date_col)
    else:
        df = pd.read_csv(path, index_col=0, parse_dates=True)

    drop_cols = [c for c in df.columns if str(c) in ("Dividends", "Stock Splits")]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    df.columns = [str(c).strip().title() for c in df.columns]

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")

    df.index = pd.to_datetime(df.index)
    df = df[~df.index.isna()].sort_index()
    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Close", "High", "Low", "Open", "Volume"])
    return df


def _merged_dataset_frames() -> List[Tuple[str, pd.DataFrame]]:
    """Collect and merge all local datasets, newest-duplicate-wins.

    Scans the legacy root (`*_10y_daily.csv`) and `daily_7y/` (`*_7y_daily.csv`
    / `.parquet`, manifest `_` files excluded). Where the two eras overlap,
    daily rows from the 7y export win over the 10y file's rows.
    """
    daily_7y_dir = os.path.join(HISTORICAL_DATA_DIR, DAILY_7Y_DIRNAME)
    groups: Dict[str, List[Tuple[int, str]]] = {}

    if os.path.isdir(HISTORICAL_DATA_DIR):
        for fname in sorted(os.listdir(HISTORICAL_DATA_DIR)):
            path = os.path.join(HISTORICAL_DATA_DIR, fname)
            if os.path.isdir(path) or fname.startswith("_"):
                continue
            if not fname.lower().endswith(".csv"):
                continue
            groups.setdefault(_instrument_key(path), []).append((0, path))

    if os.path.isdir(daily_7y_dir):
        for fname in sorted(os.listdir(daily_7y_dir)):
            path = os.path.join(daily_7y_dir, fname)
            if not os.path.isfile(path) or fname.startswith("_"):
                continue
            if not fname.lower().endswith((".csv", ".parquet")):
                continue
            groups.setdefault(_instrument_key(path), []).append((1, path))

    merged_sets: List[Tuple[str, pd.DataFrame]] = []
    for instrument, entries in sorted(groups.items()):
        frames = []
        try:
            for _, path in sorted(entries, key=lambda e: e[0]):
                frames.append(_load_dataset_frame(path))
        except Exception as e:
            print(f"[tournament] Skipping dataset for {instrument}: {e}")
            continue
        combined = frames[0] if len(frames) == 1 else pd.concat(frames).sort_index()
        if len(frames) > 1:
            combined = combined[~combined.index.duplicated(keep="last")]
        if len(combined) < 60:
            continue
        merged_sets.append((instrument, combined))
    return merged_sets


def _split_walk_forward(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split into in-sample (<= IS_END_YEAR) and out-of-sample (> IS_END_YEAR).

    Returns (None, None) when either slice is too short to test meaningfully.
    """
    years = df.index.year
    is_df = df[years <= IS_END_YEAR]
    oos_df = df[years > IS_END_YEAR]
    if len(is_df) < 120 or len(oos_df) < 60:
        return None, None
    return is_df, oos_df


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute core technical indicators across price series."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # Moving Averages
    df["sma_10"] = close.rolling(10).mean()
    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["ema_9"] = close.ewm(span=9).mean()
    df["ema_20"] = close.ewm(span=20).mean()
    df["ema_21"] = close.ewm(span=21).mean()
    df["ema_50"] = close.ewm(span=50).mean()

    # KAMA (Kaufman Adaptive Moving Average)
    # Optimization: Extract underlying NumPy 1D arrays prior to the sequential loop.
    # Pandas Series .iloc[i] indexing inside iterative loops incurs ~5-6x overhead due
    # to index alignment and scalar wrapper coercion.
    change = (close - close.shift(10)).abs()
    volatility = close.diff().abs().rolling(10).sum()
    er = change / (volatility + 1e-9)
    sc = (er * (2 / 3 - 2 / 31) + 2 / 31) ** 2
    c_arr = close.to_numpy()
    sc_arr = sc.to_numpy()
    n_len = len(c_arr)
    kama = np.full(n_len, np.nan, dtype=np.float64)
    if n_len > 0:
        kama[0] = c_arr[0]
    for i in range(1, n_len):
        s = sc_arr[i]
        # Hold the prior value through the warm-up: a NaN smoothing constant
        # would otherwise poison the recursion (NaN + x = NaN) and leave the
        # whole series invalid, silently turning strategy 6 permanently short.
        kama[i] = kama[i - 1] + (s * (c_arr[i] - kama[i - 1]) if not np.isnan(s) else 0.0)
    df["close_kama"] = kama

    # RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Stochastic Oscillator (%K, %D)
    low_14 = low.rolling(14).min()
    high_14 = high.rolling(14).max()
    df["stoch_k"] = 100 * ((close - low_14) / (high_14 - low_14 + 1e-9))
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Williams %R
    df["williams_r"] = -100 * ((high_14 - close) / (high_14 - low_14 + 1e-9))

    # CCI (Commodity Channel Index 20)
    tp = (high + low + close) / 3
    tp_ma = tp.rolling(20).mean()
    md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df["cci"] = (tp - tp_ma) / (0.015 * md + 1e-9)

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()

    # ATR 14
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    # Bollinger Bands
    df["bb_mid"] = close.rolling(20).mean()
    std = close.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2.0 * std
    df["bb_lower"] = df["bb_mid"] - 2.0 * std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_mid"] + 1e-9)
    df["bb_width_ma"] = df["bb_width"].rolling(20).mean()

    # Donchian Channels (20-day)
    df["donchian_high"] = high.rolling(20).max()
    df["donchian_low"] = low.rolling(20).min()

    # 52-Week High/Low (252-day)
    df["high_252"] = high.rolling(252).max()

    # Volume & Order Flow
    vol_ma = volume.rolling(20).mean()
    df["vol_ratio"] = volume / (vol_ma + 1e-9)
    df["vwap_20"] = (close * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)

    obv = (np.sign(close.diff().fillna(0.0)) * volume).cumsum()
    df["obv"] = obv
    df["obv_ma"] = obv.rolling(20).mean()

    # Money Flow Index (MFI 14)
    raw_mf = tp * volume
    pos_mf = np.where(tp > tp.shift(1), raw_mf, 0.0)
    neg_mf = np.where(tp < tp.shift(1), raw_mf, 0.0)
    mfr = pd.Series(pos_mf, index=df.index).rolling(14).sum() / (pd.Series(neg_mf, index=df.index).rolling(14).sum() + 1e-9)
    df["mfi_14"] = 100 - (100 / (1 + mfr))

    # Chaikin Money Flow (CMF 20)
    mfv = np.where((high - low) > 0, (((close - low) - (high - close)) / (high - low)) * volume, 0.0)
    df["cmf_20"] = pd.Series(mfv, index=df.index).rolling(20).sum() / (volume.rolling(20).sum() + 1e-9)

    # Volume Price Trend (VPT)
    vpt = (volume * (close.diff() / (close.shift(1) + 1e-9))).fillna(0.0).cumsum()
    df["vpt"] = vpt
    df["vpt_ma"] = vpt.rolling(14).mean()

    # Accumulation / Distribution Line
    clv = np.where((high - low) > 0, ((close - low) - (high - close)) / (high - low), 0.0)
    ad_line = (clv * volume).cumsum()
    df["ad_line"] = ad_line
    df["ad_line_ma"] = pd.Series(ad_line, index=df.index).rolling(20).mean()

    # ADX (14)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_smooth = tr.rolling(14).sum()
    df["plus_di"] = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).sum() / (tr_smooth + 1e-9))
    df["minus_di"] = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).sum() / (tr_smooth + 1e-9))
    dx = 100 * (df["plus_di"] - df["minus_di"]).abs() / (df["plus_di"] + df["minus_di"] + 1e-9)
    df["adx_14"] = dx.rolling(14).mean()

    # Volatility (20 vs 60)
    ret = close.pct_change()
    df["volatility_20"] = ret.rolling(20).std()
    df["volatility_60"] = ret.rolling(60).std()

    # Ichimoku Tenkan/Kijun
    df["tenkan_sen"] = (high.rolling(9).max() + low.rolling(9).min()) / 2
    df["kijun_sen"] = (high.rolling(26).max() + low.rolling(26).min()) / 2

    return df


def _supertrend(df: pd.DataFrame, period: int = 10, mult: float = 3.0) -> pd.Series:
    """
    Real SuperTrend indicator: HL2 +/- mult*ATR(period) bands that trail the
    prior band and only tighten in the direction of the trend. Returns the
    position state series (+1 long / -1 short / 0 during warm-up).
    """
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.rolling(period).mean()

    hl2 = (high + low) / 2
    ub = (hl2 + mult * atr).to_numpy()
    lb = (hl2 - mult * atr).to_numpy()
    close_np = close.to_numpy()

    n = len(df)
    final_ub = ub.copy()
    final_lb = lb.copy()
    direction = np.zeros(n)
    trend_active = False
    prev_dir = 1

    for i in range(1, n):
        if np.isnan(ub[i]) or np.isnan(lb[i]):
            direction[i] = 0
            continue
        final_ub[i] = ub[i] if (ub[i] < final_ub[i - 1] or close_np[i - 1] > final_ub[i - 1]) else final_ub[i - 1]
        final_lb[i] = lb[i] if (lb[i] > final_lb[i - 1] or close_np[i - 1] < final_lb[i - 1]) else final_lb[i - 1]
        if not trend_active:
            # Seed on the first valid bar versus the PRIOR pivot — a rising
            # market has today's close above yesterday's HL2, and vice versa.
            hl2_np = hl2.to_numpy()
            seed_ref = hl2_np[i - 1]
            direction[i] = 1 if close_np[i] >= seed_ref else -1
            trend_active = True
            prev_dir = direction[i]
            continue
        if prev_dir > 0:
            direction[i] = -1 if close_np[i] < final_lb[i] else 1
        else:
            direction[i] = 1 if close_np[i] > final_ub[i] else -1
        prev_dir = direction[i]

    return pd.Series(direction, index=df.index)


def _parabolic_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    """
    Wilder's Parabolic SAR. Returns the trend state series
    (+1 while SAR trails below price, -1 while it trails above).
    """
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    n = len(df)
    trend = np.zeros(n)
    if n < 2:
        return pd.Series(trend, index=df.index)

    direction = 1
    ep = high[0]
    sar = low[0]
    af = af_step
    trend[0] = 1

    for i in range(1, n):
        sar = sar + af * (ep - sar)

        if direction > 0:
            # SAR must not overshoot the last two lows
            sar = min(sar, low[i - 1], low[i - 2] if i > 1 else low[i - 1])
            if low[i] < sar:
                # flip to short
                direction = -1
                sar = ep
                ep = low[i]
                af = af_step
            elif high[i] > ep:
                ep = high[i]
                af = min(af_max, af + af_step)
        else:
            sar = max(sar, high[i - 1], high[i - 2] if i > 1 else high[i - 1])
            if high[i] > sar:
                # flip to long
                direction = 1
                sar = ep
                ep = high[i]
                af = af_step
            elif low[i] < ep:
                ep = low[i]
                af = min(af_max, af + af_step)
        trend[i] = direction

    return pd.Series(trend, index=df.index)


def simulate_strategy(
    df: pd.DataFrame,
    strat_id: int,
    initial_capital: float = 100_000.0,
    side_cost_bps: float = None,
    params: Dict[str, Any] = None,
    precomputed_indicators: pd.DataFrame = None,
) -> Dict[str, Any]:
    """Execute strategy simulation and compute performance metrics.

    `params` carries calibrated parameter overrides (see PARAM_GRID), e.g.
    SuperTrend {"atr_len": 14, "mult": 2.5}, Bollinger {"bb_std": 2.5},
    volume surge {"vol_mult": 1.5}. `precomputed_indicators` lets the
    tournament engine evaluate many variants against one indicator snapshot
    instead of recomputing `with rolling.apply` per variant.
    """
    params = params or {}
    df = (
        precomputed_indicators
        if precomputed_indicators is not None
        else _compute_indicators(df.copy())
    )
    close = df["Close"]
    signals = np.zeros(len(df))

    # Explicit, Distinct Signal Formula for Every Single Strategy (1-30)
    if strat_id == 1:    # SMA Dual Cross (20/50)
        signals = np.where(df["sma_20"] > df["sma_50"], 1, -1)
    elif strat_id == 2:  # EMA Fast Momentum (9/21)
        signals = np.where(df["ema_9"] > df["ema_21"], 1, -1)
    elif strat_id == 3:  # Triple MA System (10/20/50)
        signals = np.where((df["ema_9"] > df["sma_20"]) & (df["sma_20"] > df["sma_50"]), 1, -1)
    elif strat_id == 4:  # SuperTrend Quant (calibrated ATR len + multiplier)
        # Real SuperTrend: HL2 +/- mult*ATR(atr_len) trailing bands with state flips.
        signals = _supertrend(
            df, period=int(params.get("atr_len", 10)), mult=float(params.get("mult", 3.0))
        ).to_numpy()
    elif strat_id == 5:  # Parabolic SAR Acceleration (AF 0.02/0.2)
        signals = _parabolic_sar(df, af_step=0.02, af_max=0.2).to_numpy()
    elif strat_id == 6:  # KAMA Adaptive Moving Average
        signals = np.where(close > df["close_kama"], 1, -1)

    elif strat_id == 7:  # RSI Reversion (30/70)
        signals = np.where(df["rsi_14"] < 30, 1, np.where(df["rsi_14"] > 70, -1, 0))
    elif strat_id == 8:  # RSI Bull/Bear Divergence
        signals = np.where((close < close.shift(5)) & (df["rsi_14"] > df["rsi_14"].shift(5)), 1, np.where((close > close.shift(5)) & (df["rsi_14"] < df["rsi_14"].shift(5)), -1, 0))
    elif strat_id == 9:  # Stochastic Oscillator
        signals = np.where((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_d"]), 1, np.where((df["stoch_k"] > 80) & (df["stoch_k"] < df["stoch_d"]), -1, 0))
    elif strat_id == 10: # Bollinger Bands Bounce (calibrated std + RSI extremity)
        # Confluence reversion: a lower/upper band touch must be confirmed by
        # an RSI extreme (<30 / >70). Band std is a calibrated param (2.0/2.5).
        bb_std = float(params.get("bb_std", 2.0))
        std20 = close.rolling(20).std()
        lo_band = df["bb_mid"] - bb_std * std20
        hi_band = df["bb_mid"] + bb_std * std20
        rsi = df["rsi_14"]
        signals = np.where(
            (close < lo_band) & (rsi < 30),
            1,
            np.where((close > hi_band) & (rsi > 70), -1, 0),
        )
    elif strat_id == 11: # Williams %R Reversal
        signals = np.where(df["williams_r"] < -80, 1, np.where(df["williams_r"] > -20, -1, 0))
    elif strat_id == 12: # Commodity Channel Index (CCI 20)
        signals = np.where(df["cci"] < -100, 1, np.where(df["cci"] > 100, -1, 0))

    elif strat_id == 13: # Donchian Channel Breakout (20-Day)
        signals = np.where(close >= df["donchian_high"].shift(1), 1, np.where(close <= df["donchian_low"].shift(1), -1, 0))
    elif strat_id == 14: # Keltner Channel Squeeze
        signals = np.where(close > (df["ema_20"] + 2.0 * df["atr_14"]), 1, np.where(close < (df["ema_20"] - 2.0 * df["atr_14"]), -1, 0))
    elif strat_id == 15: # ATR Trailing Stop Breakout
        signals = np.where(close > (close.shift(1) + 2.5 * df["atr_14"].shift(1)), 1, -1)
    elif strat_id == 16: # Bollinger Squeeze Expansion
        signals = np.where((df["bb_width"] < df["bb_width_ma"]) & (close > df["bb_mid"]), 1, -1)
    elif strat_id == 17: # High Volume Surge Breakout (calibrated vol multiplier)
        vol_mult = float(params.get("vol_mult", 2.0))
        signals = np.where((close > close.shift(1)) & (df["vol_ratio"] > vol_mult), 1, 0)
    elif strat_id == 18: # 52-Week High Breakout
        # Breakout is measured against the PRIOR 252-bar high; the rolling
        # window includes the current bar, so comparing against it unshifted
        # can only fire when close exactly equals the 252-bar high (never).
        signals = np.where(close > df["high_252"].shift(1), 1, 0)

    elif strat_id == 19: # VWAP Dynamic Reversion
        signals = np.where(close < (df["vwap_20"] - 1.5 * df["atr_14"]), 1, np.where(close > (df["vwap_20"] + 1.5 * df["atr_14"]), -1, 0))
    elif strat_id == 20: # OBV Trend
        signals = np.where(df["obv"] > df["obv_ma"], 1, -1)
    elif strat_id == 21: # MFI 14 Reversals
        signals = np.where(df["mfi_14"] < 20, 1, np.where(df["mfi_14"] > 80, -1, 0))
    elif strat_id == 22: # CMF 20 Breakout
        signals = np.where(df["cmf_20"] > 0.15, 1, np.where(df["cmf_20"] < -0.15, -1, 0))
    elif strat_id == 23: # VPT Divergence
        signals = np.where(df["vpt"] > df["vpt_ma"], 1, -1)
    elif strat_id == 24: # Accumulation / Distribution Spike
        signals = np.where(df["ad_line"] > df["ad_line_ma"], 1, -1)

    elif strat_id == 25: # MACD + RSI Confluence
        signals = np.where((df["macd"] > df["macd_signal"]) & (df["rsi_14"] > 50), 1, -1)
    elif strat_id == 26: # ADX Trend Strength Filter
        signals = np.where((df["adx_14"] > 25) & (df["plus_di"] > df["minus_di"]), 1, -1)
    elif strat_id == 27: # Sharpe Rank Volatility Sizing
        # Inverse-volatility sizing: hold the 20/50 EMA trend, but scale
        # exposure down when short-term volatility expands (Sharpe-optimal
        # coarse sizing). Never shorts just because vol is elevated.
        vol_ratio = df["volatility_20"] / (df["volatility_60"] + 1e-9)
        size = np.clip(1.0 / (vol_ratio + 1e-9), 0.3, 1.0)
        direction = np.where(df["ema_20"] > df["ema_50"], 1, -1)
        signals = size * direction
    elif strat_id == 28: # Multi-Timeframe Trend Confirmation
        signals = np.where((df["ema_9"] > df["ema_21"]) & (df["sma_50"] > df["sma_50"].shift(5)), 1, -1)
    elif strat_id == 29: # Ichimoku Cloud Kumo Breakout
        # Full Kumo breakout with proper 26-bar displacement of the cloud.
        kumo_a = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)
        kumo_src = (df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2
        kumo_b = kumo_src.shift(26)
        kumo_hi = np.maximum(kumo_a, kumo_b)
        kumo_lo = np.minimum(kumo_a, kumo_b)
        signals = np.where(close > kumo_hi, 1, np.where(close < kumo_lo, -1, 0))
    elif strat_id == 30: # Apex Regime-Adaptive Quant Strategy
        # Regime gate: only act when ADX confirms a directional regime and
        # volume participation is elevated; flat in choppy tape.
        trending = df["adx_14"] > 20
        expanding = df["vol_ratio"] > 1.2
        long_regime = trending & expanding & (df["plus_di"] > df["minus_di"]) & (df["rsi_14"] > 50)
        short_regime = trending & expanding & (df["minus_di"] > df["plus_di"]) & (df["rsi_14"] < 50)
        signals = np.where(long_regime, 1, np.where(short_regime, -1, 0))
    elif strat_id == 31: # Volatility-Targeted Momentum (12% annualized vol target)
        # Trend-follows with explicit vol targeting: exposure is scaled so the
        # strategy risks a constant ~12% annualized volatility, shrinking in
        # volatile tape and capping at full size in calm trends.
        target_daily_vol = 0.12 / math.sqrt(252)
        vol20 = df["volatility_20"] + 1e-9
        size = np.clip(target_daily_vol / vol20, 0.25, 1.0)
        direction = np.where(df["ema_20"] > df["ema_50"], 1, -1)
        signals = size * direction
    elif strat_id == 32: # Gap & Go Breakaway Momentum
        # Breakaway-gap momentum with state persistence: a bullish gap that
        # holds above the prior day's high on 1.5x volume starts (and keeps) a
        # long until a mirror-image bearish gap flips it; events persist via
        # forward-fill rather than decaying back to flat each bar.
        gap_long = (
            (df["Open"] > close.shift(1) + 0.5 * df["atr_14"].shift(1))
            & (close > df["Open"])
            & (df["vol_ratio"] > 1.5)
            & (close > df["High"].shift(1))
        )
        gap_short = (
            (df["Open"] < close.shift(1) - 0.5 * df["atr_14"].shift(1))
            & (close < df["Open"])
            & (df["vol_ratio"] > 1.5)
            & (close < df["Low"].shift(1))
        )
        event = np.where(gap_long, 1.0, np.where(gap_short, -1.0, np.nan))
        signals = pd.Series(event, index=df.index).ffill().fillna(0.0).to_numpy()

    # Warm-up guard: rows whose indicator inputs are still NaN must stay flat.
    # NaN comparisons evaluate False, so `a > b` styles silently go SHORT
    # through the warm-up window and pollute every always-in-market strategy.
    indicator_cols = [c for c in df.columns if c not in ("Open", "High", "Low", "Close", "Volume")]
    valid_rows = ~df[indicator_cols].isna().any(axis=1)
    signals = np.where(valid_rows.to_numpy(), signals, 0.0)

    # Performance Simulation
    # Cost-aware: every execution (open/close/flip/size change) pays the
    # modeled NSE per-side cost. Flip-churn strategies can no longer look free.
    returns = close.pct_change().fillna(0.0)
    position = pd.Series(signals, index=df.index).shift(1).fillna(0.0)
    turns = position.diff().abs()
    turns.iloc[0] = abs(position.iloc[0])
    cost_rate = (side_cost_bps if side_cost_bps is not None else CostEngine().side_cost_bps) / CostEngine.BPS
    strat_returns = returns * position - cost_rate * turns

    total_return_pct = float(np.round(((1 + strat_returns).prod() - 1) * 100, 2))

    # Trade-level stats: a trade is each run of a constant non-zero position.
    # The old bar-level win rate (share of positive bars) just tracked the
    # market's drift and made the leaderboard's 30% win-rate weight meaningless.
    in_market = position != 0
    run_id = (position != position.shift(1)).cumsum()
    trade_returns = strat_returns[in_market].groupby(run_id[in_market]).sum()
    total_trades = int(len(trade_returns))
    winning_trades = int((trade_returns > 0).sum())
    win_rate = round((winning_trades / total_trades) * 100, 1) if total_trades else 0.0

    # Profit factor: gross wins / gross losses (mandate target: > 1.5).
    # Capped at 99.99 so JSON serialization never sees infinity.
    gross_wins = float(trade_returns[trade_returns > 0].sum())
    gross_losses = float(-trade_returns[trade_returns < 0].sum())
    if gross_losses > 1e-12:
        profit_factor = min(round(gross_wins / gross_losses, 2), 99.99)
    else:
        profit_factor = 99.99 if gross_wins > 1e-12 else 0.0

    cum_returns = (1 + strat_returns).cumprod()
    peak = cum_returns.cummax()
    drawdown = (cum_returns - peak) / peak
    max_dd = float(np.round(abs(drawdown.min()) * 100, 2))

    mean_ret = strat_returns.mean()
    std_ret = strat_returns.std()
    sharpe = float(np.round((mean_ret / (std_ret + 1e-9)) * np.sqrt(252), 2))
    cagr = float(np.round((((cum_returns.iloc[-1]) ** (252 / max(len(df), 1))) - 1) * 100, 2)) if len(df) > 0 else 0.0

    return {
        "strat_id": strat_id,
        "strategy": STRATEGY_REGISTRY[strat_id]["name"],
        "bucket": STRATEGY_REGISTRY[strat_id]["bucket"],
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr,
        "win_rate": win_rate,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd,
        "total_trades": total_trades,
        "final_capital": round(initial_capital * (1 + total_return_pct / 100), 2),
        "cost_paid_pct": float(np.round(cost_rate * turns.sum() * 100, 2)),
        "avg_turnover": float(np.round(turns.mean(), 3)),
        "profit_factor": profit_factor,
        "selected_params": dict(params) if params else {},
    }


def _tournament_score(avg_sharpe: float, avg_win_rate: float, avg_return: float, avg_dd: float) -> float:
    """
    Composite ranking score with unit-coherent components (each mapped to a
    bounded scale, weighted, summed). The old raw mix let a +800% return term
    (160 pts) drown Sharpe (±2 pts), so the ranking was effectively
    "highest return wins" regardless of risk or consistency.
    """
    sharpe_term = 40.0 * max(-1.0, min(2.0, avg_sharpe) / 2.0)        # -20..+40
    win_term = 30.0 * (max(0.0, min(100.0, avg_win_rate)) / 100.0)    # 0..+30
    ret_term = 20.0 * max(-1.0, math.tanh(avg_return / 100.0))        # -20..+20
    dd_term = 10.0 * min(1.0, max(0.0, avg_dd) / 50.0)                # 0..-10 penalty
    return float(np.round(sharpe_term + win_term + ret_term - dd_term, 2))


def run_full_tournament() -> List[Dict[str, Any]]:
    """
    30-Strategy Quant Tournament — walk-forward calibration edition.

    Per dataset (all merged local history):
      1. Split into In-Sample (2019-2023) and Out-of-Sample (2024-2026).
      2. Compute indicators exactly once per phase/dataset, then evaluate every
         parameter-grid variant for each strategy on the IS slice.
      3. Select the best variant by IS Sharpe, then replay it unmodified on the
         OOS slice — no peeking, no re-tuning.
      4. Final score = 0.40 * IS composite + 0.60 * OOS composite, with the
         overfit gap (IS score - OOS score) reported so inflated variants are
         visible rather than hidden.

    Indicator precomputation replaces the legacy design where indicators were
    recomputed 30x per dataset (which made full runs time out): rolling
    windows — including a lambda-based CCI — are computed once per phase and
    shared across all strategy variants of that dataset.
    """
    if not os.path.isdir(HISTORICAL_DATA_DIR):
        return []

    datasets = _merged_dataset_frames()

    acc: Dict[int, Dict[str, Any]] = {
        sid: {
            "is_sharpe": [], "is_win": [], "is_ret": [], "is_dd": [], "is_score": [],
            "selected": [],
            "oos_sharpe": [], "oos_win": [], "oos_ret": [], "oos_dd": [], "oos_score": [],
            "oos_trades": [], "oos_cost": [], "oos_pf": [],
        }
        for sid in STRATEGY_REGISTRY
    }

    for instrument, df_all in datasets:
        is_df, oos_df = _split_walk_forward(df_all)
        if is_df is None:
            print(
                f"[tournament] Skipping {instrument}: walk-forward slices too short "
                f"(IS {len(is_df) if is_df is not None else 0} rows, OOS {len(oos_df) if oos_df is not None else 0} rows)"
            )
            continue
        try:
            is_ind = _compute_indicators(is_df.copy())
            oos_ind = _compute_indicators(oos_df.copy())
        except Exception as e:
            print(f"[tournament] Skipping {instrument}: indicator computation failed: {e}")
            continue

        for strat_id in STRATEGY_REGISTRY:
            best_params: Dict[str, Any] = {}
            best_is: Dict[str, Any] = None
            for params in get_param_grid(strat_id):
                try:
                    res = simulate_strategy(
                        is_df, strat_id, params=params, precomputed_indicators=is_ind
                    )
                except Exception as e:
                    print(f"[tournament] {instrument} IS strat {strat_id} failed: {e}")
                    best_is = None
                    break
                if best_is is None or res["sharpe_ratio"] > best_is["sharpe_ratio"]:
                    best_params, best_is = params, res
            if best_is is None:
                continue

            try:
                oos_res = simulate_strategy(
                    oos_df, strat_id, params=best_params, precomputed_indicators=oos_ind
                )
            except Exception as e:
                print(f"[tournament] {instrument} OOS strat {strat_id} failed: {e}")
                continue

            a = acc[strat_id]
            a["selected"].append(dict(best_params))
            a["is_sharpe"].append(best_is["sharpe_ratio"])
            a["is_win"].append(best_is["win_rate"])
            a["is_ret"].append(best_is["total_return_pct"])
            a["is_dd"].append(best_is["max_drawdown_pct"])
            a["is_score"].append(_tournament_score(
                best_is["sharpe_ratio"], best_is["win_rate"],
                best_is["total_return_pct"], best_is["max_drawdown_pct"]))
            a["oos_sharpe"].append(oos_res["sharpe_ratio"])
            a["oos_win"].append(oos_res["win_rate"])
            a["oos_ret"].append(oos_res["total_return_pct"])
            a["oos_dd"].append(oos_res["max_drawdown_pct"])
            a["oos_trades"].append(oos_res["total_trades"])
            a["oos_cost"].append(oos_res["cost_paid_pct"])
            a["oos_pf"].append(oos_res["profit_factor"])
            a["oos_score"].append(_tournament_score(
                oos_res["sharpe_ratio"], oos_res["win_rate"],
                oos_res["total_return_pct"], oos_res["max_drawdown_pct"]))

    results = []
    for strat_id, a in acc.items():
        if not a["is_score"]:
            continue
        info = STRATEGY_REGISTRY[strat_id]

        def _avg(key: str, decimals: int) -> float:
            return float(np.round(np.mean(a[key]), decimals)) if a[key] else 0.0

        is_score = _avg("is_score", 2)
        oos_score = _avg("oos_score", 2)
        final_score = float(np.round(IS_WEIGHT * is_score + OOS_WEIGHT * oos_score, 2))

        # Prune/retire: negative-expectancy strategies out of sample (OOS
        # composite <= 0 across datasets) are marked RETIRED so the live
        # trainer and execution layer exclude them entirely.
        status = "RETIRED" if oos_score <= 0.0 else "ACTIVE"

        # Most-selected parameter variant across datasets ({} for param-free)
        variant_counts = Counter(
            tuple(sorted(v.items())) for v in a["selected"]
        )
        selected_params = dict(variant_counts.most_common(1)[0][0]) if variant_counts else {}

        results.append({
            "strat_id": strat_id,
            "strategy": info["name"],
            "bucket": info["bucket"],
            "score": final_score,
            "status": status,
            "total_return_pct": _avg("oos_ret", 2),
            "win_rate": _avg("oos_win", 1),
            "sharpe_ratio": _avg("oos_sharpe", 2),
            "max_drawdown_pct": _avg("oos_dd", 2),
            "profit_factor": _avg("oos_pf", 2),
            "datasets_tested": len(a["is_score"]),
            # walk-forward diagnostics
            "in_sample_score": is_score,
            "out_of_sample_score": oos_score,
            "is_sharpe": _avg("is_sharpe", 2),
            "is_win_rate": _avg("is_win", 1),
            "is_total_return_pct": _avg("is_ret", 2),
            "is_max_drawdown_pct": _avg("is_dd", 2),
            "oos_trades_avg": _avg("oos_trades", 1),
            "oos_cost_paid_avg_pct": _avg("oos_cost", 2),
            "overfit_degradation_pct": float(np.round(is_score - oos_score, 2)),
            "walk_forward_weights": {"in_sample": IS_WEIGHT, "out_of_sample": OOS_WEIGHT},
            "selected_params": selected_params,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return results


if __name__ == "__main__":
    print("Running 30-Strategy Quant Tournament (walk-forward IS 2019-23 / OOS 2024-26)...")
    print("Datasets: legacy 10y CSVs merged with daily_7y (csv+parquet)")
    results = run_full_tournament()
    print(f"Tournament Complete! Evaluated {len(results)} strategies.")
    for r in results[:10]:
        params = r["selected_params"] or "-"
        print(
            f"Rank #{r['rank']}: {r['strategy']} (Bucket: {r['bucket']}, "
            f"Score: {r['score']} = IS {r['in_sample_score']} + OOS {r['out_of_sample_score']}, "
            f"WinRate: {r['win_rate']}%, Sharpe(OOS): {r['sharpe_ratio']}, "
            f"Return(OOS): {r['total_return_pct']}%, Degradation: {r['overfit_degradation_pct']}%, "
            f"Params: {params})"
        )
