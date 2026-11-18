"""Backtesting API endpoints with Nautilus Trader and Lean."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.core.security import CsrfDep
from app.services.nautilus_engine import (
    get_nautilus_engine,
    list_strategies,
    get_strategy,
    BacktestResult,
    ApexTradeStrategy,
    OpeningRangeBreakout,
    TrendFollowing,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    strategy: str = Field(..., description="Strategy name")
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    start_date: str = Field(..., description="ISO format start date")
    end_date: str = Field(..., description="ISO format end date")
    initial_capital: float = Field(default=100000, gt=0)
    interval: str = Field(default="15min", description="Bar interval")
    engine: str = Field(default="nautilus", description="Backtest engine: nautilus or lean")


@router.get("/strategies")
async def get_strategies() -> Dict:
    """List available backtest strategies."""
    strategies = {
        "opening_range_breakout": {
            "name": "Opening Range Breakout",
            "description": "Trades breakouts from the opening range (first 15 minutes)",
            "parameters": {
                "or_minutes": {"type": "int", "default": 15, "description": "Opening range minutes"},
                "risk_per_trade": {"type": "float", "default": 0.02, "description": "Risk per trade"},
            },
        },
        "trend_following": {
            "name": "EMA Trend Following",
            "description": "Trades EMA crossover signals",
            "parameters": {
                "fast_ema": {"type": "int", "default": 9, "description": "Fast EMA period"},
                "slow_ema": {"type": "int", "default": 21, "description": "Slow EMA period"},
                "risk_per_trade": {"type": "float", "default": 0.02},
            },
        },
        "vwap_reversion": {
            "name": "VWAP Mean Reversion",
            "description": "Trades reversions to VWAP",
            "parameters": {
                "vwap_period": {"type": "int", "default": 20},
                "std_dev": {"type": "float", "default": 2.0},
                "risk_per_trade": {"type": "float", "default": 0.02},
            },
        },
    }
    return {"strategies": strategies}


@router.post("/run")
async def run_backtest(
    request: BacktestRequest,
    db: Session = DbDep,
    session: dict = SessionDep,
    csrf=CsrfDep,
) -> dict:
    """Run backtest using Nautilus Trader or Lean."""
    raise HTTPException(status_code=501, detail="Backtest execution not yet implemented")


@router.get("/results/{backtest_id}")
async def get_backtest_result(
    backtest_id: str,
    db: Session = DbDep,
    session: dict = SessionDep,
) -> Dict:
    """Get stored backtest result."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/history")
async def get_backtest_history(
    db: Session = DbDep,
    session: dict = SessionDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> Dict:
    """Get backtest history."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.delete("/{backtest_id}")
async def delete_backtest(
    backtest_id: str,
    db: Session = DbDep,
    session: dict = SessionDep,
    csrf=CsrfDep,
) -> Dict:
    """Delete backtest result."""
    raise HTTPException(status_code=501, detail="Not yet implemented")