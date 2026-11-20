"""
backend/quant/market_regime.py — NSE Market Regime Classifier
=============================================================
Classifies the NIFTY 50 daily macro-regime used by the strategy engines:

- TRENDING_BULLISH : price > EMA50, EMA20 > EMA50, EMA50 rising
- TRENDING_BEARISH : price < EMA50, EMA20 < EMA50, EMA50 falling
- VOLATILE         : short-term (20d) volatility materially above the
                     medium-term (60d) baseline — regime labels are unreliable
- RANGING          : everything else (choppy tape, no directional trend)
- UNCLEAR          : insufficient data / data pipeline failure

All strategies that take the daily macro context into account must read this
classifier, never re-derive their own ad-hoc regime.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
import pandas as pd

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Regime vol threshold: 20d realized vol >= 1.4x the 60d baseline -> chop risk
VOL_BLOWOUT_RATIO = 1.4
_MIN_BARS = 80


class MarketRegimeClassifier:
    """NIFTY 50 macro-regime classifier with local-first data sourcing."""

    def __init__(self, lookback_bars: int = 260):
        self.lookback_bars = int(lookback_bars)
        self._df: Optional[pd.DataFrame] = None

    # ── Data sourcing ─────────────────────────────────────────────────────────
    def load_data(self, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Load NIFTY 50 daily bars: local merged history first, yfinance fallback."""
        if not force_refresh and self._df is not None:
            return self._df

        df: Optional[pd.DataFrame] = None

        try:  # reuse the tournament engine's dataset merge (10y legacy + 7y exports)
            from strategy_tournament import _merged_dataset_frames

            for instrument, frame in _merged_dataset_frames():
                if instrument == "NIFTY_50_INDEX":
                    df = frame
                    break
        except Exception as e:  # noqa: BLE001 - data sourcing is best-effort
            print(f"[market_regime] local NIFTY_50_INDEX load failed: {e}")

        if df is None:
            try:
                import yfinance as yf  # type: ignore

                raw = yf.download("^NSEI", period="2y", interval="1d", progress=False)
                if raw is not None and len(raw) > 0:
                    if isinstance(raw.columns, pd.MultiIndex):
                        raw.columns = raw.columns.get_level_values(0)
                    raw.columns = [str(c).strip().title() for c in raw.columns]
                    if {"Open", "High", "Low", "Close", "Volume"}.issubset(raw.columns):
                        df = raw
            except Exception as e:  # noqa: BLE001
                print(f"[market_regime] yfinance ^NSEI fallback failed: {e}")

        if df is not None and len(df) > self.lookback_bars:
            df = df.iloc[-self.lookback_bars:]

        self._df = df
        return df

    # ── Classification ────────────────────────────────────────────────────────
    def classify_regime(self) -> Dict:
        """Classify the current NIFTY 50 regime from daily bars.

        Returns a dict with at least:
          regime             label above
          nifty_above_ema50  True/False (None when UNCLEAR)
          nifty_close, nifty_ema20, nifty_ema50, nifty_vol_ratio_20_60
        """
        df = self._df if self._df is not None else self.load_data()
        unclear = {
            "regime": "UNCLEAR",
            "nifty_above_ema50": None,
            "nifty_close": None,
            "nifty_ema20": None,
            "nifty_ema50": None,
            "nifty_vol_ratio_20_60": None,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        if df is None or len(df) < _MIN_BARS or "Close" not in df.columns:
            return unclear

        try:
            close = df["Close"].astype(float)
            ema20 = close.ewm(span=20).mean()
            ema50 = close.ewm(span=50).mean()
            ret = close.pct_change()
            vol20 = ret.rolling(20).std()
            vol60 = ret.rolling(60).std()
            vol_ratio = float((vol20 / (vol60 + 1e-12)).iloc[-1])

            last_close = float(close.iloc[-1])
            last_ema20 = float(ema20.iloc[-1])
            last_ema50 = float(ema50.iloc[-1])
            ema50_slope = float(ema50.diff(10).iloc[-1])

            above_ema50 = bool(last_close > last_ema50)
            if vol_ratio >= VOL_BLOWOUT_RATIO:
                regime = "VOLATILE"
            elif above_ema50 and last_ema20 > last_ema50 and ema50_slope > 0:
                regime = "TRENDING_BULLISH"
            elif (not above_ema50) and last_ema20 < last_ema50 and ema50_slope < 0:
                regime = "TRENDING_BEARISH"
            else:
                regime = "RANGING"

            if not all(np.isfinite(x) for x in (last_close, last_ema20, last_ema50, vol_ratio)):
                return unclear

            return {
                "regime": regime,
                "nifty_above_ema50": above_ema50,
                "nifty_close": round(last_close, 2),
                "nifty_ema20": round(last_ema20, 2),
                "nifty_ema50": round(last_ema50, 2),
                "nifty_vol_ratio_20_60": round(vol_ratio, 3),
                "ema50_slope": round(ema50_slope, 4),
                "bars_used": int(len(close)),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:  # noqa: BLE001
            print(f"[market_regime] classification failed: {e}")
            return unclear
