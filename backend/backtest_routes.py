"""
backtest_routes.py
==================
FastAPI router for backtesting endpoints.
Mount this in main.py with: app.include_router(backtest_router)
"""

from fastapi import APIRouter, Query, Depends
import db
import backtest_engine
from app.core.security import require_session, require_admin

backtest_router = APIRouter(prefix="/api/backtest", tags=["backtest"])


from pydantic import BaseModel, Field
from typing import Optional

class BacktestRequest(BaseModel):
    symbol: str
    range: Optional[str] = "3mo"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capital: Optional[float] = 10000.0
    stop_atr: Optional[float] = 1.5
    target_atr: Optional[float] = 2.5
    entry_score: Optional[int] = 5
    risk_pct: Optional[float] = 2.0
    early_exit: Optional[int] = -4

@backtest_router.get("/run", dependencies=[Depends(require_session)])
def run_backtest(
    symbol: str = Query(..., description="NSE symbol to backtest"),
    range: str = Query("3mo", description="Timeframe range, e.g. 1mo, 3mo, 6mo, 1y"),
    capital: float = Query(10000.0, description="Initial backtest capital size"),
    stop_atr: float = Query(1.5, description="Stop-loss ATR multiplier"),
    target_atr: float = Query(2.5, description="Profit target ATR multiplier"),
    entry_score: int = Query(5, description="Minimum signal score for entry"),
    risk_pct: float = Query(
        2.0, description="Risk percentage per trade (e.g. 2.0 for 2%)"
    ),
    early_exit: int = Query(-4, description="Early exit score threshold"),
):
    """Run historical backtest simulation on a symbol."""
    sym = symbol.upper().strip()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"

    config = backtest_engine.BacktestConfig(
        period_range=range,
        initial_capital=capital,
        stop_atr=stop_atr,
        target_atr=target_atr,
        entry_score=entry_score,
        risk_pct=risk_pct / 100.0,
        early_exit=early_exit,
    )
    return backtest_engine.run_historical_backtest(sym, config)


@backtest_router.post("/run", dependencies=[Depends(require_session)])
def run_backtest_post(req: BacktestRequest):
    """Run historical backtest simulation via POST JSON body."""
    sym = req.symbol.upper().strip()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"

    config = backtest_engine.BacktestConfig(
        period_range=req.range or "3mo",
        initial_capital=req.capital or 10000.0,
        stop_atr=req.stop_atr or 1.5,
        target_atr=req.target_atr or 2.5,
        entry_score=req.entry_score or 5,
        risk_pct=(req.risk_pct or 2.0) / 100.0,
        early_exit=req.early_exit or -4,
    )
    return backtest_engine.run_historical_backtest(sym, config)


@backtest_router.get("/stats", dependencies=[Depends(require_session)])
def get_backtest_stats():
    """Aggregated performance statistics."""
    return db.get_stats()


@backtest_router.get("/history", dependencies=[Depends(require_session)])
def get_backtest_history(
    limit: int = Query(100, ge=1, le=500),
    symbol: str = Query(None),
    status: str = Query(None),
):
    """Full signal log with optional filters."""
    return {
        "history": db.get_history(limit=limit, symbol=symbol, status=status),
        "count": len(db.get_history(limit=limit, symbol=symbol, status=status)),
    }


@backtest_router.post("/reset", dependencies=[Depends(require_admin)])
def reset_backtest():
    """Wipe all signal history."""
    db.clear_history()
    return {"status": "ok", "message": "Signal history cleared."}
