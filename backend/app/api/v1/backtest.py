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
    BacktestResult as NautilusBacktestResult,
    ApexTradeStrategy,
    OpeningRangeBreakout,
    TrendFollowing,
)
from app.services.lean_engine import get_lean_engine, BacktestResult as LeanBacktestResult
from app.core.data_adapter import get_market_data_for_backtest

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
    try:
        # Validate dates
        try:
            start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format.")

        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        # Get historical data
        bars_df = get_market_data_for_backtest(
            db,
            symbol=request.symbol,
            interval=request.interval,
            start_date=start_date,
            end_date=end_date,
        )

        if bars_df is None or bars_df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {request.symbol} in date range")

        # Get strategy class
        strategy_class = get_strategy(request.strategy)
        if not strategy_class:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")

        # Prepare strategy config
        strategy_config = {
            'symbol': request.symbol,
            'timeframe': request.interval,
            'start_year': start_date.year,
            'start_month': start_date.month,
            'start_day': start_date.day,
            'end_year': end_date.year,
            'end_month': end_date.month,
            'end_day': end_date.day,
            'initial_capital': request.initial_capital,
            **request.strategy_params,
        }

        # Run backtest based on engine
        if request.engine == "nautilus":
            engine = get_nautilus_engine()
            if not engine.initialize():
                raise HTTPException(status_code=500, detail="Failed to initialize Nautilus engine")

            result = await engine.run_backtest(
                symbol=request.symbol,
                bars_df=bars_df,
                strategy_class=strategy_class,
                strategy_config=strategy_config,
                start_date=start_date,
                end_date=end_date,
                initial_capital=request.initial_capital,
            )
        elif request.engine == "lean":
            lean_engine = get_lean_engine()
            result = await lean_engine.run_backtest(
                symbol=request.symbol,
                bars_df=bars_df,
                strategy_class=strategy_class,
                strategy_config=strategy_config,
                start_date=start_date,
                end_date=end_date,
                initial_capital=request.initial_capital,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown engine: {request.engine}")

        return {
            "engine": result.engine,
            "symbol": result.symbol,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_return": result.total_return,
            "total_return_pct": result.total_return_pct,
            "max_drawdown": result.max_drawdown,
            "max_drawdown_pct": result.max_drawdown_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "avg_win": result.avg_win,
            "avg_loss": result.avg_loss,
            "equity_curve": result.equity_curve,
            "trades": result.trades,
            "metadata": result.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/results/{backtest_id}")
async def get_backtest_result(
    backtest_id: str,
    db: Session = DbDep,
    session: dict = SessionDep,
) -> Dict:
    """Get stored backtest result."""
    from app.db.repositories import repo

    result = repo.backtest.get(db, backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")

    return result.to_dict()


@router.get("/history")
async def get_backtest_history(
    db: Session = DbDep,
    session: dict = SessionDep,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> Dict:
    """Get backtest history."""
    from app.db.repositories import repo

    results = repo.backtest.get_history(db, limit=limit, offset=offset)
    return {"results": [r.to_dict() for r in results]}


@router.delete("/{backtest_id}")
async def delete_backtest(
    backtest_id: str,
    db: Session = DbDep,
    session: dict = SessionDep,
    csrf=CsrfDep,
) -> Dict:
    """Delete backtest result."""
    from app.db.repositories import repo

    deleted = repo.backtest.delete(db, backtest_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backtest not found")

    return {"status": "deleted", "id": backtest_id}