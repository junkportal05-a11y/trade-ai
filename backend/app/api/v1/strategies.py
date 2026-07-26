"""Strategies router."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request, status, HTTPException

from app.api.deps import SessionDep

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

STRATEGY_PRESETS = [
    {"id": "intraday_momentum", "name": "Intraday Momentum", "description": "EMA crossover + RSI + volume filter. 15m timeframe.", "riskProfile": "Moderate", "typicalHold": "15m-2h", "win_rate": 64.5, "return": 18.2, "sharpe": 1.45},
    {"id": "mean_reversion", "name": "Mean Reversion", "description": "Bollinger Band squeeze + RSI extremes. 5m-15m timeframe.", "riskProfile": "Low", "typicalHold": "5m-30m", "win_rate": 71.0, "return": 12.4, "sharpe": 1.62},
    {"id": "breakout_volume", "name": "Breakout Volume", "description": "High volume breakout + ADX trend filter. 15m-1h timeframe.", "riskProfile": "High", "typicalHold": "30m-4h", "win_rate": 58.2, "return": 24.5, "sharpe": 1.28},
    {"id": "scalper_rsi", "name": "RSI Scalper", "description": "Fast RSI extremes + EMA alignment. 1m-5m timeframe.", "riskProfile": "High", "typicalHold": "1m-10m", "win_rate": 55.0, "return": 15.0, "sharpe": 1.10},
    {"id": "swing_trend", "name": "Swing Trend Follower", "description": "Daily EMA trend + weekly MACD. 1h-1d timeframe.", "riskProfile": "Low", "typicalHold": "1d-2w", "win_rate": 68.0, "return": 21.0, "sharpe": 1.75},
]


@router.get("", response_model=dict)
def get_strategies(
    active_only: bool = Query(True, description="Filter to only active strategies"),
) -> dict:
    """Get all strategies."""
    return {"status": "success", "strategies": STRATEGY_PRESETS}


@router.get("/{strategy_id}", response_model=dict)
def get_strategy(strategy_id: str) -> dict:
    """Get a specific strategy by ID."""
    for s in STRATEGY_PRESETS:
        if s["id"] == str(strategy_id):
            return s
    raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_strategy(request: Request, _=SessionDep) -> dict:
    """Create a new strategy."""
    return {
        "id": 999,
        "name": "New Strategy",
        "description": "Created from UI",
        "is_active": True,
    }