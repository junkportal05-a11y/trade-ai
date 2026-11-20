"""Forecasting API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.core.security import CsrfDep
from app.services.forecasting.timesfm_service import forecast_price_async as timesfm_forecast
from app.services.forecasting.kronos_service import forecast_price_async as kronos_forecast
from app.services.forecasting.ensemble import forecast_ensemble_async

router = APIRouter(prefix="/api/forecast", tags=["forecasting"])


class ForecastRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50, description="Trading symbol")
    horizon: int = Field(default=64, ge=1, le=512, description="Forecast horizon")
    frequency: str = Field(default="15min", description="Data frequency")
    quantiles: List[float] = Field(default=[0.1, 0.5, 0.9], description="Quantiles to forecast")
    use_cache: bool = Field(default=True, description="Use cached forecasts")


class EnsembleForecastRequest(ForecastRequest):
    weights: Optional[Dict[str, float]] = Field(default=None, description="Custom model weights")


class ForecastResponse(BaseModel):
    model: str
    symbol: str
    forecast_horizon: int
    frequency: str
    point_forecast: List[float]
    quantile_forecasts: Dict[str, List[List[float]]]
    prediction_intervals: Dict[str, List[List[float]]]
    timestamps: List[str]
    metadata: Dict
    generated_at: str


@router.post("/timesfm", response_model=ForecastResponse)
async def forecast_timesfm(
    request: ForecastRequest,
    db: Session = DbDep,
    session: dict = SessionDep,
    csrf=CsrfDep,
) -> Dict:
    """
    Generate forecast using Google TimesFM.
    
    TimesFM is Google's foundation model for time series forecasting.
    """
    try:
        from app.services.forecasting.timesfm_service import forecast_price_async
        from app.core.data_adapter import from_angelone_response
        from app.db.repositories import repo

        # Get historical data
        history = repo.market_data.get_history(
            db,
            symbol=request.symbol,
            interval=request.frequency,
            range="60d",  # Need enough context
        )

        if not history:
            raise HTTPException(status_code=404, detail=f"No data for {request.symbol}")

        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Generate forecast
        result = await timesfm_forecast(
            df=df,
            symbol=request.symbol,
            horizon=request.horizon,
            freq=request.frequency,
            quantiles=request.quantiles,
        )

        return {
            "model": result.model,
            "symbol": result.symbol,
            "forecast_horizon": result.forecast_horizon,
            "frequency": result.frequency,
            "point_forecast": result.point_forecast,
            "quantile_forecasts": result.quantile_forecasts,
            "prediction_intervals": result.prediction_intervals,
            "timestamps": [ts.isoformat() for ts in result.timestamps],
            "metadata": result.metadata,
            "generated_at": result.generated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TimesFM forecast failed: {str(e)}")


@router.post("/kronos", response_model=ForecastResponse)
async def forecast_kronos(
    request: ForecastRequest,
    db: Session = DbDep,
    session: dict = SessionDep,
    csrf=CsrfDep,
) -> Dict:
    """
    Generate forecast using Kronos.
    
    Kronos is a financial time series foundation model.
    """
    try:
        from app.services.forecasting.kronos_service import forecast_price_async
        from app.db.repositories import repo

        history = repo.market_data.get_history(
            db,
            symbol=request.symbol,
            interval=request.frequency,
            range="60d",
        )

        if not history:
            raise HTTPException(status_code=404, detail=f"No data for {request.symbol}")

        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        result = await kronos_forecast(
            df=df,
            symbol=request.symbol,
            horizon=request.horizon,
            freq=request.frequency,
            quantiles=request.quantiles,
        )

        return {
            "model": result.model,
            "symbol": result.symbol,
            "forecast_horizon": result.forecast_horizon,
            "frequency": result.frequency,
            "point_forecast": result.point_forecast,
            "quantile_forecasts": result.quantile_forecasts,
            "prediction_intervals": result.prediction_intervals,
            "timestamps": [ts.isoformat() for ts in result.timestamps],
            "metadata": result.metadata,
            "generated_at": result.generated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kronos forecast failed: {str(e)}")


@router.post("/ensemble", response_model=ForecastResponse)
async def forecast_ensemble(
    request: EnsembleForecastRequest,
    db: Session = DbDep,
    session: dict = SessionDep,
    csrf=CsrfDep,
) -> Dict:
    """
    Generate ensemble forecast combining TimesFM, Kronos, Prophet, and Naive models.
    
    Uses adaptive weighting based on historical model performance.
    """
    try:
        from app.services.forecasting.ensemble import forecast_ensemble_async
        from app.db.repositories import repo

        history = repo.market_data.get_history(
            db,
            symbol=request.symbol,
            interval=request.frequency,
            range="60d",
        )

        if not history:
            raise HTTPException(status_code=404, detail=f"No data for {request.symbol}")

        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        result = await forecast_ensemble_async(
            df=df,
            symbol=request.symbol,
            horizon=request.horizon,
            freq=request.frequency,
            quantiles=request.quantiles,
        )

        return {
            "model": result.model,
            "symbol": result.symbol,
            "forecast_horizon": result.forecast_horizon,
            "frequency": result.frequency,
            "point_forecast": result.point_forecast,
            "quantile_forecasts": result.quantile_forecasts,
            "prediction_intervals": result.prediction_intervals,
            "timestamps": [ts.isoformat() for ts in result.timestamps],
            "component_forecasts": {
                k: {
                    "model": v.model if hasattr(v, 'model') else "Unknown",
                    "point_forecast": v.point_forecast if hasattr(v, 'point_forecast') else v.get('point_forecast', []),
                }
                for k, v in result.component_forecasts.items()
            },
            "weights": result.weights,
            "metadata": result.metadata,
            "generated_at": result.generated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ensemble forecast failed: {str(e)}")


@router.get("/models")
async def list_models() -> Dict:
    """List available forecasting models and their status."""
    from app.core.data_adapter import EngineRegistry

    available = EngineRegistry.get_available()

    models = {
        "timesfm": {
            "name": "Google TimesFM",
            "type": "Foundation Model",
            "capabilities": ["forecast", "quantiles", "covariates"],
            "available": "timesfm" in available,
            "version": "2.5",
        },
        "kronos": {
            "name": "Kronos",
            "type": "Financial Transformer",
            "capabilities": ["forecast", "quantiles", "finetune"],
            "available": "kronos" in available,
        },
        "prophet": {
            "name": "Facebook Prophet",
            "type": "Statistical",
            "capabilities": ["forecast", "seasonality", "holidays"],
            "available": "prophet" in available,
        },
        "ensemble": {
            "name": "Ensemble (TimesFM + Kronos + Prophet + Naive)",
            "type": "Ensemble",
            "capabilities": ["forecast", "quantiles", "adaptive_weighting"],
            "available": True,
        },
    }

    return {"models": models, "available_engines": available}


@router.get("/health")
async def forecast_health() -> Dict:
    """Check forecasting service health."""
    from app.core.data_adapter import get_best_engine

    return {
        "status": "healthy",
        "best_backtest_engine": get_best_engine("backtest"),
        "best_forecast_engine": get_best_engine("forecast"),
        "timestamp": datetime.utcnow().isoformat(),
    }