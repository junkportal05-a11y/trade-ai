"""TimesFM Forecasting Service for ApexTrade."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

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
    quantile_forecasts: Dict[str, List[List[float]]]  # quantile -> [timestep -> value]
    prediction_intervals: Dict[str, List[List[float]]]  # confidence -> [lower, upper]
    timestamps: List[datetime]
    input_data: Dict
    metadata: Dict
    generated_at: datetime


class TimesFMService:
    """TimesFM forecasting service wrapper."""

    def __init__(self):
        self.model = None
        self.model_version = "2.5"  # or "3.0"
        self.is_loaded = False
        self.context_length = 512
        self.prediction_length = 64

    def load_model(self, version: str = "2.5", device: str = "cuda") -> bool:
        """Load TimesFM model."""
        try:
            # Try to import timesfm
            import timesfm

            if version == "2.5":
                # TimesFM 2.5
                self.model = timesfm.TimesFm(
                    hparams=timesfm.TimesFmHparams(
                        backend="torch",
                        per_core_batch_size=32,
                        horizon_len=self.prediction_length,
                        context_len=self.context_length,
                        num_layers=20,
                        model_dims=1280,
                    ),
                    checkpoint=timesfm.TimesFmCheckpoint(
                        huggingface_repo_id="google/timesfm-2.0-500m-pytorch",
                    ),
                )
            else:
                # TimesFM 3.0
                self.model = timesfm.TimesFm(
                    hparams=timesfm.TimesFmHparams(
                        backend="torch",
                        per_core_batch_size=32,
                        horizon_len=self.prediction_length,
                        context_len=self.context_length,
                    ),
                    checkpoint=timesfm.TimesFmCheckpoint(
                        huggingface_repo_id="google/timesfm-3.0-2b-pytorch",
                    ),
                )

            self.model_version = version
            self.is_loaded = True
            logger.info(f"TimesFM {version} loaded successfully")
            return True

        except ImportError:
            logger.warning("TimesFM not installed. Install with: pip install timesfm")
            return False
        except Exception as e:
            logger.error(f"Failed to load TimesFM: {e}")
            return False

    def forecast(
        self,
        df: pd.DataFrame,
        symbol: str,
        horizon: int = 64,
        freq: str = "15min",
        quantiles: List[float] = [0.1, 0.5, 0.9],
        covariates: Optional[pd.DataFrame] = None,
    ) -> ForecastResult:
        """Generate forecast using TimesFM."""
        if not self.is_loaded:
            if not self.load_model():
                raise RuntimeError("TimesFM model not loaded")

        try:
            # Prepare input data
            input_data = self._prepare_input(df, symbol)

            # Generate forecast
            if hasattr(self.model, 'forecast'):
                point_forecast, quantile_forecast = self.model.forecast(
                    inputs=input_data['values'],
                    freq=freq,
                    horizon_len=horizon,
                    quantiles=quantiles,
                )
            else:
                # Fallback for different API
                forecast = self.model.predict(input_data['values'], horizon=horizon)
                point_forecast = forecast.mean
                quantile_forecast = forecast.quantiles

            # Generate timestamps
            last_timestamp = df['timestamp'].iloc[-1]
            timestamps = pd.date_range(
                start=last_timestamp + pd.Timedelta(freq),
                periods=horizon,
                freq=freq
            ).tolist()

            # Build result
            result = ForecastResult(
                model=f"TimesFM-{self.model_version}",
                symbol=symbol,
                forecast_horizon=horizon,
                frequency=freq,
                point_forecast=point_forecast.tolist() if hasattr(point_forecast, 'tolist') else point_forecast,
                quantile_forecasts={
                    str(q): qf.tolist() if hasattr(qf, 'tolist') else qf
                    for q, qf in zip(quantiles, quantile_forecast)
                } if isinstance(quantile_forecast, (list, np.ndarray)) else {},
                prediction_intervals=self._build_intervals(point_forecast, quantile_forecast, quantiles),
                timestamps=timestamps,
                input_data=input_data,
                metadata={
                    'model_version': self.model_version,
                    'context_length': self.context_length,
                    'prediction_length': horizon,
                    'input_length': len(input_data['values']),
                },
                generated_at=datetime.utcnow(),
            )

            return result

        except Exception as e:
            logger.error(f"TimesFM forecast failed: {e}")
            raise

    def _prepare_input(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Prepare input data for TimesFM."""
        # Use log returns for stationarity
        close_prices = df['close'].values
        log_returns = np.diff(np.log(close_prices))

        # Pad or truncate to context length
        if len(log_returns) > self.context_length:
            log_returns = log_returns[-self.context_length:]
        elif len(log_returns) < self.context_length:
            pad = np.zeros(self.context_length - len(log_returns))
            log_returns = np.concatenate([pad, log_returns])

        return {
            'values': log_returns.reshape(1, -1),
            'symbol': symbol,
            'last_price': float(df['close'].iloc[-1]),
            'last_timestamp': df['timestamp'].iloc[-1],
        }

    def _build_intervals(self, point_forecast, quantile_forecast, quantiles) -> Dict:
        """Build prediction intervals from quantile forecasts."""
        intervals = {}
        if isinstance(quantile_forecast, (list, np.ndarray)) and len(quantile_forecast) >= 2:
            # Assume symmetric quantiles around median
            lower_idx = 0
            upper_idx = -1
            for conf in [0.5, 0.8, 0.9, 0.95]:
                intervals[str(conf)] = [
                    [float(quantile_forecast[lower_idx][i]), float(quantile_forecast[upper_idx][i])]
                    for i in range(len(point_forecast))
                ]
        return intervals

    async def forecast_async(
        self,
        df: pd.DataFrame,
        symbol: str,
        horizon: int = 64,
        freq: str = "15min",
        quantiles: List[float] = [0.1, 0.5, 0.9],
    ) -> ForecastResult:
        """Async forecast wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.forecast,
            df, symbol, horizon, freq, quantiles
        )


class TimesFMForecaster:
    """High-level forecaster with caching and fallback."""

    def __init__(self):
        self.service = TimesFMService()
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def _get_cache_key(self, symbol: str, horizon: int, freq: str) -> str:
        return f"{symbol}:{horizon}:{freq}"

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
            logger.info(f"Returning cached forecast for {symbol}")
            return self.cache[key]['result']

        try:
            result = self.service.forecast(df, symbol, horizon, freq)
            self.cache[cache_key] = {
                'result': result,
                'timestamp': datetime.utcnow(),
            }
            return result
        except Exception as e:
            # Try to return stale cache on error
            if cache_key in self.cache:
                logger.warning(f"Forecast failed, returning stale cache: {e}")
                return self.cache[cache_key]['result']
            raise

    async def forecast_async(self, *args, **kwargs) -> ForecastResult:
        """Async forecast."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.forecast, *args, **kwargs)


# Global forecaster instance
_timesfm_forecaster = None


def get_timesfm_forecaster() -> TimesFMForecaster:
    """Get global TimesFM forecaster instance."""
    global _timesfm_forecaster
    if _timesfm_forecaster is None:
        _timesfm_forecaster = TimesFMForecaster()
    return _timesfm_forecaster


# Convenience functions
def forecast_price(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 64,
    freq: str = "15min",
) -> ForecastResult:
    """Quick forecast function."""
    forecaster = get_timesfm_forecaster()
    return forecaster.forecast(df, symbol, horizon, freq)


async def forecast_price_async(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 64,
    freq: str = "15min",
) -> ForecastResult:
    """Async forecast."""
    forecaster = get_timesfm_forecaster()
    return await forecaster.forecast_async(df, symbol, horizon, freq)