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

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.core.limiter import limiter, get_real_client_ip

# Custom key function to use token if present, otherwise real client IP address
def custom_key_func(request: Request) -> str:
    token = get_token_from_request(request)
    if token:
        return f"user:{token}"
    return get_real_client_ip(request)

# Override default limit with specific auth limits where needed
# These will be applied in route decorators

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    init_db()

    # Initialize worker task references to None explicitly
    app.state.agent_task = None
    app.state.resolver_task = None
    app.state.governance_task = None

    # Launch background workers as async tasks safely
    try:
        import sys
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        import trading_agent
        from trading_agent import trading_agent_loop, prediction_resolver_worker
        import governance_worker

        if hasattr(trading_agent, "prediction_resolver_worker"):
            app.state.resolver_task = asyncio.create_task(prediction_resolver_worker())

        # Start the loop as a background asyncio task
        app.state.agent_task = asyncio.create_task(trading_agent_loop())
        logger.info("trading_agent_loop task created")

        if hasattr(governance_worker, "governance_loop"):
            app.state.governance_task = asyncio.create_task(governance_worker.governance_loop())
    except Exception as exc:
        # In testing environments, log warning and continue
        if os.getenv("TESTING") or os.getenv("PYTEST_CURRENT_TEST"):
            logger.warning(f"Background worker startup skipped in test environment: {exc}")
        else:
            # In live/production, fail loud - do NOT silently continue
            logger.critical(f"Background worker startup failed: {exc}")
            app.state.worker_startup_failed = str(exc)
            raise

    yield
    # Shutdown — cancel background tasks on app close
    for task_attr in ("agent_task", "resolver_task", "governance_task"):
        if hasattr(app.state, task_attr):
            try:
                task = getattr(app.state, task_attr)
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)
trusted_hosts = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "127.0.0.1").split(",") if h.strip()]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_hosts)
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
        "total_return_pct": result.get("total_pnl_pct", 0.0) if isinstance(result, dict) else 0.0,
        "total_pnl_pct": result.get("total_pnl_pct", 0.0) if isinstance(result, dict) else 0.0,
        "max_drawdown_pct": result.get("max_drawdown", 0.0) if isinstance(result, dict) else 0.0,
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
@app.get("/api/quote", tags=["quotes"])
async def get_quote_endpoint(symbol: str):
    import app.services.quotes as quotes_svc
    quote = quotes_svc.get_symbol_quote(symbol)
    if quote is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return quote


@app.get("/", tags=["root"])
async def read_root():
    return {"status": "ok", "message": """ApexTrade AI Core Backend Engine.
"""}