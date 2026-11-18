"""Kronos Forecasting Service for ApexTrade."""
from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Import torch lazily - not in CI requirements
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

from app.core.config import settings
from app.core.data_adapter import convert_bars

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Standardized forecast result."""
    model: str
    symbol: str
    forecast_horizon: int
    frequency: str
    point_forecast: List[float]
    quantile_forecasts: Dict[str, List[List[float]]]
    prediction_intervals: Dict[str, List[List[float]]]
    timestamps: List[datetime]
    input_data: Dict
    metadata: Dict
    generated_at: datetime


class KronosService:
    """Kronos forecasting service wrapper."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False
        self.context_length = 512
        self.prediction_length = 64

        # Add Kronos to path
        kronos_path = Path(settings.KRONOS_PATH) if hasattr(settings, 'KRONOS_PATH') else Path.cwd() / "integrations" / "Kronos"
        if kronos_path.exists():
            sys.path.insert(0, str(kronos_path))
            sys.path.insert(0, str(kronos_path / "model"))

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Load Kronos model."""
        try:
            # Try to import Kronos
            from model.kronos import Kronos
            from model.tokenizer import KronosTokenizer

            # Default model path
            if model_path is None:
                model_path = "NeoQuasar/Kronos-small"  # or local path

            # Load tokenizer
            self.tokenizer = KronosTokenizer.from_pretrained(model_path)

            # Load model
            self.model = Kronos.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()

            self.is_loaded = True
            logger.info(f"Kronos model loaded on {self.device}")
            return True

        except ImportError as e:
            logger.warning(f"Kronos not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load Kronos: {e}")
            return False

    def forecast(
        self,
        df: pd.DataFrame,
        symbol: str,
        horizon: int = 64,
        freq: str = "15min",
        quantiles: List[float] = [0.1, 0.5, 0.9],
        temperature: float = 1.0,
        top_p: float = 0.9,
        num_samples: int = 100,
    ) -> ForecastResult:
        """Generate forecast using Kronos."""
        if not self.is_loaded:
            if not self.load_model():
                raise RuntimeError("Kronos model not loaded")

        try:
            import torch

            # Prepare input
            input_data = self._prepare_input(df, symbol)

            # Tokenize
            tokens = self.tokenizer.encode(input_data['values'])
            input_ids = torch.tensor([tokens], device=self.device)

            # Generate forecasts (multiple samples for uncertainty)
            all_forecasts = []
            with torch.no_grad():
                for _ in range(num_samples):
                    generated = self.model.generate(
                        input_ids,
                        max_new_tokens=horizon,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True,
                        pad_token_id=self.tokenizer.pad_token_id,
                    )
                    # Decode forecast tokens
                    forecast_tokens = generated[0, -horizon:].cpu().numpy()
                    forecast_values = self.tokenizer.decode(forecast_tokens)
                    all_forecasts.append(forecast_values)

            # Aggregate forecasts
            forecasts_array = np.array(all_forecasts)  # (num_samples, horizon)
            point_forecast = np.median(all_forecasts, axis=0)
            quantile_forecasts = {}

            for q in quantiles:
                quantile_forecasts[str(q)] = np.percentile(all_forecasts, q * 100, axis=0).tolist()

            # Generate timestamps
            last_timestamp = df['timestamp'].iloc[-1]
            timestamps = pd.date_range(
                start=last_timestamp + pd.Timedelta(freq),
                periods=horizon,
                freq=freq
            ).tolist()

            # Build result
            result = ForecastResult(
                model="Kronos",
                symbol=symbol,
                forecast_horizon=horizon,
                frequency=freq,
                point_forecast=point_forecast.tolist(),
                quantile_forecasts=quantile_forecasts,
                prediction_intervals=self._build_intervals(all_forecasts, quantiles),
                timestamps=timestamps,
                input_data=self._prepare_input(df, symbol),
                metadata={
                    'model': 'Kronos',
                    'device': self.device,
                    'context_length': self.context_length,
                    'prediction_length': horizon,
                    'num_samples': num_samples,
                    'temperature': temperature,
                },
                generated_at=datetime.utcnow(),
            )

            return result

        except Exception as e:
            logger.error(f"Kronos forecast failed: {e}")
            raise

    def _prepare_input(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Prepare input for Kronos."""
        # Kronos expects normalized price sequences
        close_prices = df['close'].values

        # Normalize by first price
        norm_prices = close_prices / close_prices[0]

        # Pad or truncate
        if len(norm_prices) > self.context_length:
            norm_prices = norm_prices[-self.context_length:]
        elif len(norm_prices) < self.context_length:
            pad = np.full(self.context_length - len(norm_prices), norm_prices[0])
            norm_prices = np.concatenate([pad, norm_prices])

        return {
            'values': norm_prices,
            'symbol': symbol,
            'last_price': float(df['close'].iloc[-1]),
            'last_timestamp': df['timestamp'].iloc[-1],
        }

    def _build_intervals(self, all_forecasts: np.ndarray, quantiles: List[float]) -> Dict:
        """Build prediction intervals."""
        intervals = {}
        for conf in [0.5, 0.8, 0.9, 0.95]:
            lower_q = (1 - conf) / 2
            upper_q = 1 - lower_q
            lower = np.percentile(all_forecasts, lower_q * 100, axis=0)
            upper = np.percentile(all_forecasts, upper_q * 100, axis=0)
            intervals[str(conf)] = [
                [float(lower[i]), float(upper[i])]
                for i in range(all_forecasts.shape[1])
            ]
        return intervals


class KronosForecaster:
    """High-level Kronos forecaster with caching."""

    def __init__(self):
        self.service = KronosService()
        self.cache = {}
        self.cache_ttl = 300

    def _get_cache_key(self, symbol: str, horizon: int, freq: str) -> str:
        return f"kronos:{symbol}:{horizon}:{freq}"

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache:
            return False
        age = (datetime.utcnow() - self.cache[key]['timestamp']).total_seconds()
        return age < self.cache_ttl

    def forecast(
        self,
        df: pd.DataFrame,
        symbol: str,
        horizon: int = 64,
        freq: str = "15min",
        use_cache: bool = True,
    ) -> ForecastResult:
        """Forecast with caching."""
        cache_key = self._get_cache_key(symbol, horizon, freq)

        if use_cache and self._is_cache_valid(cache_key):
            logger.info(f"Returning cached Kronos forecast for {symbol}")
            return self.cache[key]['result']

        try:
            result = self.service.forecast(df, symbol, horizon, freq)
            self.cache[cache_key] = {
                'result': result,
                'timestamp': datetime.utcnow(),
            }
            return result
        except Exception as e:
            if cache_key in self.cache:
                logger.warning(f"Kronos forecast failed, returning stale cache: {e}")
                return self.cache[cache_key]['result']
            raise

    async def forecast_async(self, *args, **kwargs) -> ForecastResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.forecast, *args, **kwargs)


# Global forecaster
_kronos_forecaster = None


def get_kronos_forecaster() -> KronosForecaster:
    global _kronos_forecaster
    if _kronos_forecaster is None:
        _kronos_forecaster = KronosForecaster()
    return _kronos_forecaster


# Convenience functions
def forecast_price(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 64,
    freq: str = "15min",
) -> ForecastResult:
    forecaster = get_kronos_forecaster()
    return forecaster.forecast(df, symbol, horizon, freq)


async def forecast_price_async(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 64,
    freq: str = "15min",
) -> ForecastResult:
    forecaster = get_kronos_forecaster()
    return await forecaster.forecast_async(df, symbol, horizon, freq)