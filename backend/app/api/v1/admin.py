"""Admin router."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.api.deps import DbDep, AdminDep
from app.core.security import CsrfDep
from app.core.worker_health import get_all as get_worker_health
from app.services.market_hours import is_nse_market_open

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", response_model=dict, dependencies=[AdminDep])
def admin_health(
    db: Session = DbDep,
) -> dict:
    from app.db.repositories import repo
    stats = repo.signals.get_stats(db)
    return {"status": "healthy", "signals_stats": stats, "workers": get_worker_health()}


@router.delete("/signals/clear", response_model=dict, dependencies=[CsrfDep, AdminDep])
def clear_signals(
    db: Session = DbDep,
) -> dict:
    from app.db.repositories import repo
    repo.signals.clear_all(db)
    return {"status": "cleared", "message": "All signal history cleared"}


@router.post("/run-simulation", response_model=dict, dependencies=[CsrfDep, AdminDep])
async def run_simulation(
    request: Request,
) -> dict:
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    symbol = body.get("symbol", "RELIANCE.NS")
    if not symbol.endswith(".NS") and not symbol.startswith("^"):
        symbol = f"{symbol}.NS"
        
    start_date = body.get("start_date", "2024-01-01")
    end_date = body.get("end_date", "2024-12-31")
    
    error = None
    try:
        from backtest_engine import run_historical_backtest, BacktestConfig
        config = BacktestConfig(period_range="1y", initial_capital=100000.0)
        result = run_historical_backtest(symbol, config)
        if isinstance(result, dict) and result.get("error"):
            error = str(result["error"])
    except Exception as exc:
        result = {}
        error = str(exc)

    if error is None and (not isinstance(result, dict) or not result):
        error = "backtest engine returned no data"
    ok = error is None
    return {
        "status": "completed" if ok else "failed",
        "data_source": "backtest_engine" if ok else "unavailable",
        "simulated": False,
        "error": error,
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "win_rate": result.get("win_rate") if ok else None,
        "total_pnl_pct": result.get("total_pnl_pct") if ok else None,
        "profit_factor": result.get("profit_factor") if ok else None,
        "total_trades": result.get("total_trades") if ok else None,
        "max_drawdown": result.get("max_drawdown") if ok else None,
    }


@router.get("/simulation-status", response_model=dict, dependencies=[AdminDep])
def get_simulation_status() -> dict:
    return {
        "status": "idle",
        "is_running": False,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "progress_pct": 100.0,
    }


@router.get("/worker-status", response_model=dict, dependencies=[AdminDep])
def admin_worker_status(request: Request) -> dict:
    from app.core.worker_health import get_all as get_worker_health
    from app.core.worker_state import get_degraded_workers
    workers = get_worker_health()
    is_healthy = not any(w.get("status") == "degraded" for w in workers.values())
    degraded_workers = get_degraded_workers()
    degraded = bool(degraded_workers)
    try:
        from app.services.broker import get_broker_feed
        angelone_authorized = bool(get_broker_feed().is_authorized())
    except Exception:
        angelone_authorized = False
    return {
        "agent_running": is_healthy and not degraded,
        "market_open": is_nse_market_open(),
        "angelone_authorized": angelone_authorized,
        "angelone_status": "authorized" if angelone_authorized else "not_authorized",
        "status": "healthy" if is_healthy and not degraded else "degraded",
        "degraded": degraded,
        "active_monitors": ["kill_switch"],
        "workers": workers,
        "degraded_workers": degraded_workers,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
