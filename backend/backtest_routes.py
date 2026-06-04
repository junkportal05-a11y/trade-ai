"""
backtest_routes.py
==================
FastAPI router for backtesting endpoints.
Mount this in main.py with: app.include_router(backtest_router)
"""

from fastapi import APIRouter, Query
import db

backtest_router = APIRouter(prefix="/api/backtest", tags=["backtest"])


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
