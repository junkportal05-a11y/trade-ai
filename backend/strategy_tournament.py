"""
backend/strategy_tournament.py — 30-Strategy Quant Tournament Engine for ApexTrade AI
Runs 30 distinct quantitative trading strategies across all 10-year local historical CSV datasets.
"""
import os
import sys
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Any

backend_dir = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_DATA_DIR = os.path.join(backend_dir, "historical_data")

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

    # Bucket 5: Multi-Factor & Regime-Adaptive (25-30)
    25: {"name": "MACD + RSI Confluence", "bucket": "Multi-Factor"},
    26: {"name": "ADX Trend Strength Filter (ADX > 25)", "bucket": "Multi-Factor"},
    27: {"name": "Sharpe Rank Volatility Sizing", "bucket": "Multi-Factor"},
    28: {"name": "Multi-Timeframe Trend Confirmation", "bucket": "Multi-Factor"},
    29: {"name": "Ichimoku Cloud Kumo Breakout", "bucket": "Multi-Factor"},
    30: {"name": "Apex Regime-Adaptive Quant Strategy", "bucket": "Multi-Factor"},
}


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
    change = (close - close.shift(10)).abs()
    volatility = close.diff().abs().rolling(10).sum()
    er = change / (volatility + 1e-9)
    sc = (er * (2 / 3 - 2 / 31) + 2 / 31) ** 2
    kama = np.full(len(df), np.nan)
    kama[0] = close.iloc[0]
    for i in range(1, len(df)):
        s = sc.iloc[i]
        # Hold the prior value through the warm-up: a NaN smoothing constant
        # would otherwise poison the recursion (NaN + x = NaN) and leave the
        # whole series invalid, silently turning strategy 6 permanently short.
        kama[i] = kama[i - 1] + (s * (close.iloc[i] - kama[i - 1]) if not np.isnan(s) else 0.0)
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


def simulate_strategy(df: pd.DataFrame, strat_id: int, initial_capital: float = 100_000.0) -> Dict[str, Any]:
    """Execute strategy simulation and compute performance metrics."""
    df = _compute_indicators(df.copy())
    close = df["Close"]
    signals = np.zeros(len(df))

    # Explicit, Distinct Signal Formula for Every Single Strategy (1-30)
    if strat_id == 1:    # SMA Dual Cross (20/50)
        signals = np.where(df["sma_20"] > df["sma_50"], 1, -1)
    elif strat_id == 2:  # EMA Fast Momentum (9/21)
        signals = np.where(df["ema_9"] > df["ema_21"], 1, -1)
    elif strat_id == 3:  # Triple MA System (10/20/50)
        signals = np.where((df["ema_9"] > df["sma_20"]) & (df["sma_20"] > df["sma_50"]), 1, -1)
    elif strat_id == 4:  # SuperTrend Quant
        signals = np.where(close > (df["sma_20"] - 3.0 * df["atr_14"]), 1, -1)
    elif strat_id == 5:  # Parabolic SAR Acceleration
        signals = np.where(close > close.shift(1), 1, -1)
    elif strat_id == 6:  # KAMA Adaptive Moving Average
        signals = np.where(close > df["close_kama"], 1, -1)

    elif strat_id == 7:  # RSI Reversion (30/70)
        signals = np.where(df["rsi_14"] < 30, 1, np.where(df["rsi_14"] > 70, -1, 0))
    elif strat_id == 8:  # RSI Bull/Bear Divergence
        signals = np.where((close < close.shift(5)) & (df["rsi_14"] > df["rsi_14"].shift(5)), 1, np.where((close > close.shift(5)) & (df["rsi_14"] < df["rsi_14"].shift(5)), -1, 0))
    elif strat_id == 9:  # Stochastic Oscillator
        signals = np.where((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_d"]), 1, np.where((df["stoch_k"] > 80) & (df["stoch_k"] < df["stoch_d"]), -1, 0))
    elif strat_id == 10: # Bollinger Bands Bounce
        signals = np.where(close < df["bb_lower"], 1, np.where(close > df["bb_upper"], -1, 0))
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
    elif strat_id == 17: # High Volume Surge Breakout
        signals = np.where((close > close.shift(1)) & (df["vol_ratio"] > 2.0), 1, 0)
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
        signals = np.where(df["volatility_20"] < df["volatility_60"], 1, -1)
    elif strat_id == 28: # Multi-Timeframe Trend Confirmation
        signals = np.where((df["ema_9"] > df["ema_21"]) & (df["sma_50"] > df["sma_50"].shift(5)), 1, -1)
    elif strat_id == 29: # Ichimoku Cloud Kumo Breakout
        signals = np.where((close > df["tenkan_sen"]) & (df["tenkan_sen"] > df["kijun_sen"]), 1, -1)
    elif strat_id == 30: # Apex Regime-Adaptive Quant Strategy
        signals = np.where((df["vol_ratio"] > 1.5) & (df["rsi_14"] > 50) & (df["macd"] > df["macd_signal"]), 1, np.where(df["rsi_14"] < 40, -1, 0))

    # Warm-up guard: rows whose indicator inputs are still NaN must stay flat.
    # NaN comparisons evaluate False, so `a > b` styles silently go SHORT
    # through the warm-up window and pollute every always-in-market strategy.
    indicator_cols = [c for c in df.columns if c not in ("Open", "High", "Low", "Close", "Volume")]
    valid_rows = ~df[indicator_cols].isna().any(axis=1)
    signals = np.where(valid_rows.to_numpy(), signals, 0.0)

    # Performance Simulation
    returns = close.pct_change().fillna(0.0)
    position = pd.Series(signals, index=df.index).shift(1).fillna(0.0)
    strat_returns = returns * position

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
        "final_capital": round(initial_capital * (1 + total_return_pct / 100), 2)
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
    """Run all 30 strategies across all local 10-year historical CSV files."""
    csv_files = [f for f in os.listdir(HISTORICAL_DATA_DIR) if f.endswith(".csv")] if os.path.exists(HISTORICAL_DATA_DIR) else []
    if not csv_files:
        return []

    tournament_results = []
    for strat_id, info in STRATEGY_REGISTRY.items():
        all_returns = []
        all_win_rates = []
        all_drawdowns = []
        all_sharpes = []

        for csv_file in csv_files:
            file_path = os.path.join(HISTORICAL_DATA_DIR, csv_file)
            try:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                if len(df) < 30:
                    continue
                res = simulate_strategy(df, strat_id)
                all_returns.append(res["total_return_pct"])
                all_win_rates.append(res["win_rate"])
                all_drawdowns.append(res["max_drawdown_pct"])
                all_sharpes.append(res["sharpe_ratio"])
            except Exception as e:
                print(f"[tournament] Skipping {csv_file} for strategy {strat_id}: {e}")
                continue

        if all_returns:
            avg_return = float(np.round(np.mean(all_returns), 2))
            avg_win_rate = float(np.round(np.mean(all_win_rates), 1))
            avg_dd = float(np.round(np.mean(all_drawdowns), 2))
            avg_sharpe = float(np.round(np.mean(all_sharpes), 2))
            score = _tournament_score(avg_sharpe, avg_win_rate, avg_return, avg_dd)

            tournament_results.append({
                "strat_id": strat_id,
                "strategy": info["name"],
                "bucket": info["bucket"],
                "score": score,
                "total_return_pct": avg_return,
                "win_rate": avg_win_rate,
                "sharpe_ratio": avg_sharpe,
                "max_drawdown_pct": avg_dd,
                "datasets_tested": len(all_returns)
            })

    tournament_results.sort(key=lambda x: x["score"], reverse=True)
    for rank, item in enumerate(tournament_results, start=1):
        item["rank"] = rank

    return tournament_results


if __name__ == "__main__":
    print("Running 30-Strategy Quant Tournament across 26 local 10y datasets...")
    results = run_full_tournament()
    print(f"Tournament Complete! Evaluated {len(results)} strategies.")
    for r in results[:10]:
        print(f"Rank #{r['rank']}: {r['strategy']} (Bucket: {r['bucket']}, Score: {r['score']}, WinRate: {r['win_rate']}%, Sharpe: {r['sharpe_ratio']}, Return: {r['total_return_pct']}%)")
