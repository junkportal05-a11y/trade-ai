"""Ensemble Forecasting Service combining multiple models."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.config import settings
from app.services.forecasting.timesfm_service import (
    TimesFMForecaster,
    ForecastResult as TimesFMResult,
)
from app.services.forecasting.kronos_service import (
    KronosForecaster,
    ForecastResult as KronosResult,
)

logger = logging.getLogger(__name__)


@dataclass
class EnsembleForecastResult:
    """Ensemble forecast result."""
    model: str = "Ensemble"
    symbol: str = ""
    forecast_horizon: int = 0
    frequency: str = ""
    point_forecast: List[float] = field(default_factory=list)
    quantile_forecasts: Dict[str, List[List[float]]] = field(default_factory=dict)
    prediction_intervals: Dict[str, List[List[float]]] = field(default_factory=dict)
    timestamps: List[datetime] = field(default_factory=list)
    component_forecasts: Dict[str, Any] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelWeight:
    """Model weight configuration."""
    name: str
    weight: float
    enabled: bool = True
    min_accuracy: float = 0.0


class EnsembleForecaster:
    """Ensemble forecaster combining multiple models."""

    DEFAULT_WEIGHTS = {
        'timesfm': 0.4,
        'kronos': 0.3,
        'prophet': 0.2,
        'naive': 0.1,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.models = {}
        self.performance_history = {}
        self._initialize_models()

    def _initialize_models(self):
        """Initialize available models."""
        # TimesFM
        try:
            self.models['timesfm'] = TimesFMForecaster()
            logger.info("TimesFM initialized")
        except Exception as e:
            logger.warning(f"TimesFM not available: {e}")
            self.weights['timesfm'] = 0

        # Kronos
        try:
            self.models['kronos'] = KronosForecaster()
            logger.info("Kronos initialized")
        except Exception as e:
            logger.warning(f"Kronos not available: {e}")
            self.weights['kronos'] = 0

        # Prophet (optional)
        try:
            from prophet import Prophet
            self.models['prophet'] = True
            logger.info("Prophet available")
        except ImportError:
            logger.warning("Prophet not installed")
            self.weights['prophet'] = 0

        # Normalize weights
        self._normalize_weights()

    def _normalize_weights(self):
        """Normalize weights to sum to 1."""
        total = sum(w for m, w in self.weights.items() if self.weights.get(m, 0) > 0)
        if total > 0:
            for k in self.weights:
                if self.weights[k] > 0:
                    self.weights[k] /= total

    def update_weights(self, new_weights: Dict[str, float]):
        """Update model weights."""
        self.weights.update(new_weights)
        self._normalize_weights()

    def update_performance(self, model: str, accuracy: float):
        """Update model performance for adaptive weighting."""
        if model not in self.performance_history:
            self.performance_history[model] = []
        self.performance_history[model].append(accuracy)

        # Keep last 100
        if len(self.performance_history[model]) > 100:
            self.performance_history[model] = self.performance_history[model][-100:]

    def get_adaptive_weights(self) -> Dict[str, float]:
        """Calculate adaptive weights based on recent performance."""
        adaptive = {}
        for model, history in self.performance_history.items():
            if history:
                avg_acc = np.mean(history[-20:])  # Last 20 forecasts
                adaptive[model] = max(0.01, avg_acc)
            else:
                adaptive[model] = self.weights.get(model, 0)

        # Normalize
        total = sum(adaptive.values())
        if total > 0:
            for k in adaptive:
                adaptive[k] /= total

        return adaptive

    def forecast(
        self,
        df: pd.DataFrame,
        symbol: str,
        horizon: int = 64,
        freq: str = "15min",
        quantiles: List[float] = [0.1, 0.5, 0.9],
        use_adaptive: bool = False,
    ) -> EnsembleForecastResult:
        """Generate ensemble forecast."""
        component_forecasts = {}
        successful_models = []

        # Get forecasts from each model
        for model_name, model in self.models.items():
            if not self.weights.get(model_name, 0):
                continue

            try:
                if model_name == 'timesfm' and 'timesfm' in self.models:
                    result = self.models['timesfm'].forecast(df, symbol, horizon, freq, [0.1, 0.5, 0.9])
                    component_forecasts['timesfm'] = result
                    successful_models.append('timesfm')

                elif model_name == 'kronos' and 'kronos' in self.models:
                    result = self.models['kronos'].forecast(df, symbol, horizon, freq, quantiles)
                    component_forecasts['kronos'] = result
                    successful_models.append('kronos')

                elif model_name == 'prophet':
                    result = self._forecast_prophet(df, symbol, horizon, freq)
                    component_forecasts['prophet'] = result
                    successful_models.append('prophet')

            except Exception as e:
                logger.warning(f"{model_name} forecast failed: {e}")

        # Add naive forecast as baseline
        naive_result = self._naive_forecast(df, horizon)
        component_forecasts['naive'] = naive_result
        if 'naive' not in successful_models:
            successful_models.append('naive')

        # Calculate ensemble
        if not successful_models:
            raise RuntimeError("All models failed")

        # Get weights for successful models
        active_weights = {m: self.weights.get(m, 0) for m in successful_models}
        total_weight = sum(active_weights.values())
        if total_weight == 0:
            active_weights = {m: 1.0 / len(successful_models) for m in successful_models}
        else:
            for k in active_weights:
                active_weights[k] /= total_weight

        # Weighted ensemble
        ensemble_result = self._combine_forecasts(
            component_forecasts,
            active_weights,
            symbol,
            horizon,
            freq,
            quantiles,
        )

        ensemble_result.component_forecasts = component_forecasts
        ensemble_result.weights = active_weights
        ensemble_result.metadata['successful_models'] = successful_models
        ensemble_result.metadata['model_weights'] = self.weights

        return ensemble_result

    def _forecast_prophet(self, df: pd.DataFrame, symbol: str, horizon: int, freq: str) -> Dict:
        """Prophet forecast fallback."""
        from prophet import Prophet

        # Prepare data
        prophet_df = df[['timestamp', 'close']].copy()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])

        model = Prophet(daily_seasonality=True, weekly_seasonality=True)
        model.fit(prophet_df)

        future = model.make_future_dataframe(periods=horizon, freq=freq)
        forecast = model.predict(future)

        # Extract predictions
        pred_df = forecast.tail(horizon)
        point_forecast = pred_df['yhat'].values
        lower = pred_df['yhat_lower'].values
        upper = pred_df['yhat_upper'].values

        timestamps = pred_df['ds'].values

        return {
            'model': 'Prophet',
            'symbol': symbol,
            'forecast_horizon': horizon,
            'frequency': freq,
            'point_forecast': point_forecast.tolist(),
            'quantile_forecasts': {
                '0.1': lower.tolist(),
                '0.5': point_forecast.tolist(),
                '0.9': upper.tolist(),
            },
            'prediction_intervals': {
                '0.8': [[float(lower[i]), float(upper[i])] for i in range(horizon)],
            },
            'timestamps': timestamps.tolist(),
        }

    def _naive_forecast(self, df: pd.DataFrame, horizon: int) -> Dict:
        """Naive forecast (last value carried forward)."""
        last_price = df['close'].iloc[-1]
        return {
            'model': 'Naive',
            'symbol': df.get('symbol', ['UNKNOWN'])[0] if 'symbol' in df.columns else 'UNKNOWN',
            'forecast_horizon': horizon,
            'frequency': '15min',
            'point_forecast': [float(last_price)] * horizon,
            'quantile_forecasts': {
                '0.1': [float(last_price)] * horizon,
                '0.5': [float(last_price)] * horizon,
                '0.9': [float(last_price)] * horizon,
            },
            'prediction_intervals': {
                '0.5': [[float(last_price), float(last_price)]] * horizon,
            },
        }

    def _combine_forecasts(
        self,
        forecasts: Dict[str, Dict],
        weights: Dict[str, float],
        symbol: str,
        horizon: int,
        freq: str,
        quantiles: List[float],
    ) -> EnsembleForecastResult:
        """Combine forecasts using weighted average."""
        # Get timestamps from first successful forecast
        first_forecast = next(iter(forecasts.values()))
        timestamps = first_forecast.get('timestamps', [])
        if not timestamps:
            last_time = datetime.utcnow()
            timestamps = [
                last_time + timedelta(minutes=15 * (i + 1))
                for i in range(horizon)
            ]

        # Weighted point forecast
        point_forecast = np.zeros(horizon)
        for model_name, forecast in forecasts.items():
            weight = weights.get(model_name, 0)
            pf = forecast.get('point_forecast', [])
            if len(pf) == horizon:
                point_forecast += weight * np.array(pf)

        # Weighted quantiles
        quantile_forecasts = {}
        for q in quantiles:
            q_str = str(q)
            combined = np.zeros(horizon)
            for model_name, forecast in forecasts.items():
                weight = weights.get(model_name, 0)
                qf = forecast.get('quantile_forecasts', {}).get(q_str, [])
                if len(qf) == horizon:
                    combined += weight * np.array(qf)
            quantile_forecasts[q_str] = combined.tolist()

        # Weighted intervals
        prediction_intervals = {}
        for conf in ['0.5', '0.8', '0.9', '0.95']:
            combined = np.zeros((horizon, 2))
            for model_name, forecast in forecasts.items():
                weight = weights.get(model_name, 0)
                intervals = forecast.get('prediction_intervals', {}).get(conf, [])
                if len(intervals) == horizon:
                    combined += weight * np.array(intervals)
            prediction_intervals[conf] = combined.tolist()

        return EnsembleForecastResult(
            symbol=symbol,
            forecast_horizon=horizon,
            frequency=freq,
            point_forecast=point_forecast.tolist(),
            quantile_forecasts=quantile_forecasts,
            prediction_intervals=prediction_intervals,
            timestamps=timestamps,
            metadata={
                'ensemble_method': 'weighted_average',
                'component_models': list(weights.keys()),
            },
        )

    async def forecast_async(self, *args, **kwargs) -> EnsembleForecastResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.forecast, *args, **kwargs)


# Global ensemble forecaster
_ensemble_forecaster = None


def get_ensemble_forecaster() -> EnsembleForecaster:
    global _ensemble_forecaster
    if _ensemble_forecaster is None:
        _ensemble_forecaster = EnsembleForecaster()
    return _ensemble_forecaster


def forecast_ensemble(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 64,
    freq: str = "15min",
    quantiles: List[float] = [0.1, 0.5, 0.9],
) -> EnsembleForecastResult:
    """Quick ensemble forecast."""
    forecaster = get_ensemble_forecaster()
    return forecaster.forecast(df, symbol, horizon, freq, quantiles)


async def forecast_ensemble_async(
    df: pd.DataFrame,
    symbol: str,
    horizon: int = 64,
    freq: str = "15min",
    quantiles: List[float] = [0.1, 0.5, 0.9],
) -> EnsembleForecastResult:
    forecaster = get_ensemble_forecaster()
    return await forecaster.forecast_async(df, symbol, horizon, freq, quantiles)