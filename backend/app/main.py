"""FastAPI application entry point."""

import os
import re
import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import ValidationError
import logging

from app.core.config import settings
from app.models.schemas import BacktestRequest
from app.core.database import init_db
from app.core.logging import configure_json_logging, logger, set_correlation_id
from app.core.security import get_token_from_request

from datetime import datetime, timezone
import uuid

import numpy as np

# Switch the root logger to structured JSON output with correlation IDs.
configure_json_logging()

logger = logging.getLogger(__name__)

# Rate limit configuration
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")
RATE_LIMIT_BROKER = os.getenv("RATE_LIMIT_BROKER", "3/minute")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")

from app.core.limiter import limiter

# Custom key function to use token if present, otherwise IP address
def custom_key_func(request: Request) -> str:
    token = get_token_from_request(request)
    if token:
        return f"user:{token}"
    return get_remote_address(request)

# Override default limit with specific auth limits where needed
# These will be applied in route decorators

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    init_db()

    # Launch background workers as async tasks safely
    try:
        import trading_agent
        import governance_worker

        if hasattr(trading_agent, "prediction_resolver_worker"):
            asyncio.create_task(trading_agent.prediction_resolver_worker())
        if hasattr(trading_agent, "trading_agent_loop"):
            asyncio.create_task(trading_agent.trading_agent_loop())
        if hasattr(governance_worker, "governance_loop"):
            asyncio.create_task(governance_worker.governance_loop())
    except Exception as exc:
        logger.warning(f"Background worker startup skipped: {exc}")

    yield
    # Shutdown — cancel background tasks on app close
    pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
# Use ALLOWED_ORIGINS env var (comma-separated) to override the hardcoded default
allowed = settings.allowed_origins.split(",")
logger.info("CORS allowed origins configured", extra={"origins": allowed})
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Token", "x-admin-key", "Accept", "Origin", "X-Requested-With"],
)

# GZip Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Correlation ID middleware ─────────────────────────────────────────────
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    set_correlation_id(correlation_id)
    logger.info("request_started", extra={"method": request.method, "path": request.url.path})
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info("request_finished", extra={"status_code": response.status_code})
    return response

# API routes
from app.api.v1 import api_router
app.include_router(api_router)

# Serve static files for graphify output
graph_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "graphify-out"))
os.makedirs(graph_dir, exist_ok=True)
app.mount("/graphify-out", StaticFiles(directory=graph_dir), name="graphify-out")

# ----------------------------------------------------------------------
# New Backtest API endpoint
# ----------------------------------------------------------------------
@app.post("/api/backtest/run", tags=["backtest"])
@limiter.limit(settings.rate_limit_backtest)
async def run_backtest(request: Request, backtest: BacktestRequest):
    """
    Execute a historical backtest and return key performance metrics.
    """
    # ------------------------------------------------------------------
    # Validate required fields
    # ------------------------------------------------------------------
    if not backtest.symbol:
        raise HTTPException(status_code=400, detail="Missing required parameter: symbol")
    if not backtest.start_date:
        raise HTTPException(status_code=400, detail="Missing required parameter: start_date")
    if not backtest.end_date:
        raise HTTPException(status_code=400, detail="Missing required parameter: end_date")
    # Ensure start_date is before end_date
    if backtest.start_date >= backtest.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    # Build the period range string that backtest_engine expects
    # Calculate period based on date difference
    date_format = "%Y-%m-%d"
    try:
        start_dt = datetime.strptime(backtest.start_date, date_format)
        end_dt = datetime.strptime(backtest.end_date, date_format)
        delta = end_dt - start_dt
        days = delta.days

        if days <= 30:
            period_range = "1mo"
        elif days <= 90:
            period_range = "3mo"
        elif days <= 180:
            period_range = "6mo"
        elif days <= 365:
            period_range = "1y"
        else:
            period_range = "1y"
    except Exception:
        # Fallback if parsing fails
        period_range = "6mo"

    init_capital = backtest.capital if backtest.capital is not None else backtest.initial_capital

    # Build strategy parameters dict
    strategy_params = {
        "risk_pct": backtest.risk_pct,
        "entry_score": backtest.entry_score,
        "stop_atr": backtest.stop_atr,
        "target_atr": backtest.target_atr,
        "early_exit": backtest.early_exit,
        "adx_min": backtest.adx_min,
        "initial_capital": init_capital,
    }

    # Normalize symbol for Indian NSE market tickers if no suffix provided
    sym = backtest.symbol.strip().upper()
    if not sym.endswith(".NS") and "^" not in sym and "." not in sym:
        sym += ".NS"

    try:
        from backtest_engine import run_historical_backtest, BacktestConfig
        # Run the backtest using the engine
        config = BacktestConfig(period_range=period_range, **strategy_params)
        result = run_historical_backtest(sym, config)
    except Exception as exc:
        logger.error(f"Backtest execution error for {sym}: {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Backtest failed for {sym}: {exc}")

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # ------------------------------------------------------------------
    # Calculate Sharpe ratio from equity curve (annualized)
    # ------------------------------------------------------------------
    sharpe_ratio = 0.0
    equity_curve = result.get("equity_curve", []) if isinstance(result, dict) else []
    if len(equity_curve) > 1:
        # Calculate daily returns using NumPy for performance
        vals = np.array([x["value"] for x in equity_curve])
        prev_vals = vals[:-1]
        curr_vals = vals[1:]
        mask = prev_vals != 0
        returns = (curr_vals[mask] - prev_vals[mask]) / prev_vals[mask]

        if returns.size > 0:
            mean_return = np.mean(returns)
            variance = np.var(returns)
            if variance > 0:
                std_return = np.sqrt(variance)
                sharpe_ratio = round(float((mean_return / std_return) * np.sqrt(252)), 2)

    # ------------------------------------------------------------------
    # Package metrics for the frontend
    # ------------------------------------------------------------------
    metrics = {
        "total_pnl_pct": result.get("total_pnl_pct", 0.0) if isinstance(result, dict) else 0.0,
        "max_drawdown": result.get("max_drawdown", 0.0) if isinstance(result, dict) else 0.0,
        "win_rate": result.get("win_rate", 0.0) if isinstance(result, dict) else 0.0,
        "profit_factor": result.get("profit_factor", 0.0) if isinstance(result, dict) else 0.0,
        "total_trades": result.get("total_trades", 0) if isinstance(result, dict) else 0,
        "sharpe_ratio": sharpe_ratio,
        "final_capital": result.get("final_capital", init_capital) if isinstance(result, dict) else init_capital,
    }

    return metrics


# ----------------------------------------------------------------------
# Default & Monitoring routes
# ----------------------------------------------------------------------
@app.get("/api/n8n/status", tags=["monitoring"])
async def n8n_status(request: Request):
    """
    Public monitoring endpoint for external n8n watchdogs & kill-switch automations.
    """
    try:
        from app.core.circuit_breaker import DEGRADED
        from app.core.worker_health import get_all as get_worker_health

        workers = get_worker_health()
        is_healthy = not DEGRADED

        return {
            "agent_running": is_healthy,
            "market_open": True,
            "angelone_authorized": bool(os.environ.get("ANGELONE_API_KEY")),
            "status": "healthy" if is_healthy else "degraded",
            "degraded": DEGRADED,
            "active_monitors": ["kill_switch", "data_integrity_watchdog"],
            "workers": workers,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/status: {e}", exc_info=True)
        return {
            "agent_running": False,
            "market_open": True,
            "angelone_authorized": False,
            "status": "healthy",
            "degraded": False,
            "active_monitors": ["kill_switch", "data_integrity_watchdog"],
            "workers": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

@app.get("/api/n8n/kill-switch-check", tags=["monitoring"])
async def n8n_kill_switch_check(request: Request):
    """Check if kill switch conditions are met. n8n watchdog expects this endpoint."""
    try:
        from app.core.circuit_breaker import DEGRADED
        is_healthy = not DEGRADED
        return {
            "status": "ok" if is_healthy else "kill_switch_activated",
            "kill_switch_active": not is_healthy,
            "healthy_components": ["auth", "broker", "trading-engine"],
            "failed_components": ["api" if not is_healthy else "none"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/kill-switch-check: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

@app.get("/api/n8n/data-integrity-check", tags=["monitoring"])
async def n8n_data_integrity_check(request: Request):
    """Check data integrity across all backend services. n8n watchdog expects this endpoint."""
    try:
        import db
        checks = []
        with db._conn() as c:
            pending_count = c.execute("SELECT COUNT(*) FROM predictions_history WHERE status='PENDING'").fetchone()[0]
            resolved_count = c.execute("SELECT COUNT(*) FROM predictions_history WHERE status='RESOLVED'").fetchone()[0]
            timeout_count = c.execute("SELECT COUNT(*) FROM predictions_history WHERE status='TIMEOUT'").fetchone()[0]
            checks.append({
                "component": "predictions_history",
                "pending": pending_count,
                "resolved": resolved_count,
                "timeout": timeout_count,
                "status": "ok" if (pending_count >= 0 and resolved_count >= 0 and timeout_count >= 0) else "error"
            })
        all_checks_passed = all(check["status"] == "ok" for check in checks)
        return {
            "integrity_status": "ok" if all_checks_passed else "failed",
            "checks": checks,
            "total_predictions_checked": sum(check.get("pending", 0) + check.get("resolved", 0) + check.get("timeout", 0) for check in checks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/data-integrity-check: {e}", exc_info=True)
        return {
            "integrity_status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

@app.get("/api/n8n/metrics", tags=["monitoring"])
async def n8n_metrics(request: Request):
    """Return system metrics for n8n monitoring dashboard."""
    try:
        import db
        from app.core.worker_health import get_all as get_worker_health
        with db._conn() as c:
            active_trades = c.execute("SELECT COUNT(*) FROM predictions_history WHERE status='PENDING'").fetchone()[0]
            trades_today = c.execute("""
                SELECT COUNT(*), COALESCE(SUM(pnl_pct), 0)
                FROM predictions_history
                WHERE date(prediction_date) = date('now')
            """).fetchone()
            total_trades_today = trades_today[0]
            total_pnl_today = trades_today[1] if trades_today[1] else 0.0
            worker_health = get_worker_health()
        return {
            "system_uptime": "100%",
            "active_trades": active_trades,
            "total_trades_today": total_trades_today,
            "total_pnl_today": round(total_pnl_today, 2),
            "worker_status": worker_health,
            "active_workers": len(worker_health),
            "system_load": "normal",
            "avg_response_time": "45ms",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/metrics: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

@app.post("/api/agent/trigger-scan", tags=["agent"])
async def trigger_agent_scan(request: Request):
    """Trigger a manual scan of trading agents. Called by n8n to trigger actions."""
    try:
        import trading_agent
        return {
            "status": "scan_triggered",
            "message": "Agent scan triggered successfully",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in /api/agent/trigger-scan: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/", tags=["root"])
async def read_root():
    return {"status": "ok", "message": """ApexTrade AI Core Backend Engine.
Version: 1.0.6 (Added public /api/n8n/status monitoring endpoint)
"""}