"""
Market Regime Classifier — Phase 1

Uses ADX (14-day) for trend strength and ATR (14-day) percentiles
for volatility to classify the current market into one of 4 regimes:

  TRENDING  — ADX > 25, clear directional movement
  RANGING   — ADX < 20, ATR below 80th historical percentile
  VOLATILE  — ATR above 80th historical percentile (regardless of ADX)
  UNCLEAR   — Boundary / contradictory signals (ADX 20-25 zone, or
              ADX says trend but volatility is extreme)

Designed to be called from signals.py and trading_agent.py
"""

import pandas as pd
import numpy as np
import logging
import os
from app.core.logging import logger

logger = logging.getLogger("MarketRegime")

# ── Regime Constants ────────────────────────────────────────────────────────
REGIME_TRENDING  = "TRENDING"
REGIME_RANGING   = "RANGING"
REGIME_VOLATILE  = "VOLATILE"
REGIME_UNCLEAR   = "UNCLEAR"

# ── Thresholds ──────────────────────────────────────────────────────────────
ADX_TRENDING_THRESHOLD = 25       # ADX above this = strong trend
ADX_RANGING_CEILING    = 20       # ADX below this = no trend at all
ATR_VOLATILE_PERCENTILE = 80      # ATR above this percentile = volatile
ATR_LOOKBACK_WINDOW    = 100      # Rolling window for ATR percentile calc


class MarketRegimeClassifier:
    """
    Pure classifier: takes OHLC data, computes ADX + ATR, classifies regime.
    No side effects, no database calls, no network requests.
    """

    def __init__(self, parquet_path: str = None):
        self.parquet_path = parquet_path or os.path.join(
            "historical_data", "quant", "regime", "NIFTY50_1d_10Y.parquet"
        )
        self._df = None

    def load_data(self, df: pd.DataFrame = None):
        """Load OHLC data from parquet or accept a DataFrame directly."""
        if df is not None:
            self._df = df.copy()
            return

        if not os.path.exists(self.parquet_path):
            raise FileNotFoundError(f"Nifty data not found at: {self.parquet_path}")

        self._df = pd.read_parquet(self.parquet_path)
        logger.info(f"Loaded {len(self._df)} rows from {self.parquet_path}")

    @staticmethod
    def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range (ATR) — Wilder's smoothing.
        """
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Wilder's smoothing (exponential with alpha = 1/period)
        atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        return atr

    @staticmethod
    def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index (ADX) — Wilder's method.
        Returns a Series of ADX values.
        """
        # +DM and -DM
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        # ATR for DI normalization
        atr = MarketRegimeClassifier.compute_atr(high, low, close, period)

        # Smoothed +DI and -DI
        smooth_plus_dm = plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        smooth_minus_dm = minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        # Guard against zero ATR (Series division: replace 0 with NaN so no inf)
        safe_atr = atr.replace(0, np.nan)
        plus_di = 100 * smooth_plus_dm / safe_atr
        minus_di = 100 * smooth_minus_dm / safe_atr

        # DX
        di_sum = plus_di + minus_di
        di_diff = (plus_di - minus_di).abs()
        dx = 100 * di_diff / di_sum.replace(0, np.nan)

        # ADX = smoothed DX
        adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        return adx

    def classify_regime(self, as_of_index: int = -1) -> dict:
        """
        Classify the market regime at a specific point in the data.

        Args:
            as_of_index: Row index to classify at. Default -1 (latest).

        Returns:
            dict with keys: regime, adx, atr, atr_percentile, reasoning
        """
        if self._df is None:
            raise RuntimeError("No data loaded. Call load_data() first.")

        df = self._df.copy()

        # Ensure we have required columns
        required = ['High', 'Low', 'Close']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Compute indicators on full history
        df['ATR'] = self.compute_atr(df['High'], df['Low'], df['Close'], period=14)
        df['ADX'] = self.compute_adx(df['High'], df['Low'], df['Close'], period=14)

        # Use RELATIVE ATR (ATR / Close * 100) for percentile comparison.
        # Absolute ATR is meaningless on a compounding series — a stock at ₹20000
        # will always have higher absolute ATR than one at ₹200, even if both
        # have identical percentage volatility.
        # Handle division by zero in ATR_Rel calculation
        close_prices = df['Close']
        atr_values = df['ATR']
        df['ATR_Rel'] = (atr_values / close_prices.replace(0, np.nan)) * 100

        # Rolling percentile: where does today's relative ATR sit vs last N days?
        df['ATR_Pct'] = df['ATR_Rel'].rolling(window=ATR_LOOKBACK_WINDOW, min_periods=20).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100,
            raw=False
        )

        # Get the row we're classifying
        row = df.iloc[as_of_index]
        adx_val = row.get('ADX', np.nan)
        atr_val = row.get('ATR', np.nan)
        atr_pct = row.get('ATR_Pct', np.nan)

        if pd.isna(adx_val) or pd.isna(atr_pct):
            return {
                "regime": REGIME_UNCLEAR,
                "adx": float(adx_val) if not pd.isna(adx_val) else None,
                "atr": float(atr_val) if not pd.isna(atr_val) else None,
                "atr_percentile": float(atr_pct) if not pd.isna(atr_pct) else None,
                "reasoning": "Insufficient data for classification"
            }

        adx_val = float(adx_val)
        atr_val = float(atr_val)
        atr_pct = float(atr_pct)

        # ── Classification Logic ──────────────────────────────────────────
        # Priority 1: Extreme volatility overrides everything
        if atr_pct >= ATR_VOLATILE_PERCENTILE:
            if adx_val > ADX_TRENDING_THRESHOLD:
                # High volatility + strong trend = UNCLEAR (contradictory)
                # A trending market shouldn't have extreme vol — could be a blowoff
                regime = REGIME_UNCLEAR
                reasoning = (
                    f"ADX={adx_val:.1f} says trend, but ATR is at {atr_pct:.0f}th percentile "
                    f"(extreme volatility). Contradictory — classified UNCLEAR."
                )
            else:
                regime = REGIME_VOLATILE
                reasoning = (
                    f"ATR at {atr_pct:.0f}th historical percentile (above {ATR_VOLATILE_PERCENTILE}th). "
                    f"ADX={adx_val:.1f} confirms no clean trend. Market is volatile/choppy."
                )

        # Priority 2: Strong trend
        elif adx_val > ADX_TRENDING_THRESHOLD:
            regime = REGIME_TRENDING
            reasoning = (
                f"ADX={adx_val:.1f} (above {ADX_TRENDING_THRESHOLD}). "
                f"ATR at {atr_pct:.0f}th percentile (normal). Strong directional trend."
            )

        # Priority 3: No trend, low volatility = ranging
        elif adx_val < ADX_RANGING_CEILING:
            regime = REGIME_RANGING
            reasoning = (
                f"ADX={adx_val:.1f} (below {ADX_RANGING_CEILING}). "
                f"ATR at {atr_pct:.0f}th percentile. Market is range-bound."
            )

        # Priority 4: ADX in the 20-25 dead zone
        else:
            regime = REGIME_UNCLEAR
            reasoning = (
                f"ADX={adx_val:.1f} is in the ambiguous 20-25 zone. "
                f"ATR at {atr_pct:.0f}th percentile. Cannot confidently classify."
            )

        return {
            "regime": regime,
            "adx": adx_val,
            "atr": atr_val,
            "atr_percentile": atr_pct,
            "reasoning": reasoning
        }

    def classify_history(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Classify every day in a date range. Useful for backtesting and analysis.

        Returns a DataFrame with columns: Date, Regime, ADX, ATR, ATR_Percentile
        """
        if self._df is None:
            raise RuntimeError("No data loaded. Call load_data() first.")

        df = self._df.copy()

        df['ATR'] = self.compute_atr(df['High'], df['Low'], df['Close'], period=14)
        df['ADX'] = self.compute_adx(df['High'], df['Low'], df['Close'], period=14)
        df['ATR_Rel'] = (df['ATR'] / df['Close'].replace(0, np.nan)) * 100
        df['ATR_Pct'] = df['ATR_Rel'].rolling(window=ATR_LOOKBACK_WINDOW, min_periods=20).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100,
            raw=False
        )

        # Filter date range if specified
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        results = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            adx_val = row.get('ADX', np.nan)
            atr_pct = row.get('ATR_Pct', np.nan)

            if pd.isna(adx_val) or pd.isna(atr_pct):
                regime = REGIME_UNCLEAR
            elif atr_pct >= ATR_VOLATILE_PERCENTILE:
                if adx_val > ADX_TRENDING_THRESHOLD:
                    regime = REGIME_UNCLEAR
                else:
                    regime = REGIME_VOLATILE
            elif adx_val > ADX_TRENDING_THRESHOLD:
                regime = REGIME_TRENDING
            elif adx_val < ADX_RANGING_CEILING:
                regime = REGIME_RANGING
            else:
                regime = REGIME_UNCLEAR

            results.append({
                "Date": df.index[idx],
                "Close": row.get('Close', np.nan),
                "Regime": regime,
                "ADX": round(adx_val, 2) if not pd.isna(adx_val) else None,
                "ATR": round(row.get('ATR', np.nan), 2) if not pd.isna(row.get('ATR', np.nan)) else None,
                "ATR_Percentile": round(atr_pct, 1) if not pd.isna(atr_pct) else None,
            })

        return pd.DataFrame(results)

    def get_current_regime(self) -> str:
        """Convenience: returns just the regime string for the latest data point."""
        result = self.classify_regime(as_of_index=-1)
        return result["regime"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    classifier = MarketRegimeClassifier()
    classifier.load_data()
    result = classifier.classify_regime()
    logger.info(f"\nCurrent Market Regime: {result['regime']}")
    logger.info(f"  ADX:            {result['adx']:.2f}")
    logger.info(f"  ATR:            {result['atr']:.2f}")
    logger.info(f"  ATR Percentile: {result['atr_percentile']:.1f}%")
    logger.info(f"  Reasoning:      {result['reasoning']}")