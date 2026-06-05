"""
backtest_routes.py
==================
FastAPI router for backtesting endpoints.
Mount this in main.py with: app.include_router(backtest_router)
"""

from fastapi import APIRouter, Query
import db
import backtest_engine

backtest_router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@backtest_router.get("/run")
def run_backtest(
    symbol: str = Query(..., description="NSE symbol to backtest"),
    range: str = Query("3mo", description="Timeframe range, e.g. 1mo, 3mo, 6mo, 1y"),
    capital: float = Query(10000.0, description="Initial backtest capital size"),
    stop_atr: float = Query(1.5, description="Stop-loss ATR multiplier"),
    target_atr: float = Query(2.5, description="Profit target ATR multiplier"),
    entry_score: int = Query(5, description="Minimum signal score for entry"),
    risk_pct: float = Query(2.0, description="Risk percentage per trade (e.g. 2.0 for 2%)")
):
    """Run historical backtest simulation on a symbol."""
    sym = symbol.upper().strip()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"
    return backtest_engine.run_historical_backtest(
        sym, range, capital, stop_atr, target_atr, entry_score, risk_pct / 100.0
    )


@backtest_router.get("/stats")
def get_backtest_stats():
    """Aggregated performance statistics."""
    return db.get_stats()


@backtest_router.get("/history")
def get_backtest_history(
    limit:  int = Query(100, ge=1, le=500),
    symbol: str = Query(None),
    status: str = Query(None),
):
    """Full signal log with optional filters."""
    return {
        "history": db.get_history(limit=limit, symbol=symbol, status=status),
        "count":   len(db.get_history(limit=limit, symbol=symbol, status=status)),
    }


@backtest_router.post("/reset")
def reset_backtest():
    """Wipe all signal history."""
    db.clear_history()
    return {"status": "ok", "message": "Signal history cleared."}
