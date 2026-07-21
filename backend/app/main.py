"""FastAPI application entry point."""
from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import api_router
from app.core.logging import configure_json_logging, logger, set_correlation_id

from datetime import datetime
import uuid

# Switch the root logger to structured JSON output with correlation IDs.
configure_json_logging()

# Import backtest utilities
from backtest_engine import run_historical_backtest, BacktestConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    init_db()
    yield
    # Shutdown
    pass


limiter = Limiter(key_func=get_remote_address)

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
app.include_router(api_router)

# Serve static files for graphify output
graph_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "graphify-out"))
os.makedirs(graph_dir, exist_ok=True)
app.mount("/graphify-out", StaticFiles(directory=graph_dir), name="graphify-out")


# ----------------------------------------------------------------------
# New Backtest API endpoint
# ----------------------------------------------------------------------
@app.get("/api/backtest/run", tags=["backtest"])
@limiter.limit("5/minute")
async def run_backtest(
    request: Request,
    symbol: str,
    start_date: str,
    end_date: str,
    risk_pct: float = 0.02,
    entry_score: int = 5,
    stop_atr: float = 1.5,
    target_atr: float = 2.5,
    early_exit: int = -4,
    adx_min: float = 0.0,
    initial_capital: float = 10000.0,
):
    """
    Execute a historical backtest and return key performance metrics.

    Query parameters:
        - symbol: Trading symbol (e.g., "RELIANCE")
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
        - risk_pct: Risk percentage per trade (default: 0.02)
        - entry_score: Minimum entry score (default: 5)
        - stop_atr: Stop loss ATR multiplier (default: 1.5)
        - target_atr: Take profit ATR multiplier (default: 2.5)
        - early_exit: Early exit score threshold (default: -4)
        - adx_min: Minimum ADX for trend filter (default: 0.0)
        - initial_capital: Starting capital (default: 10000.0)

    Returns JSON with metrics:
        {
            "total_pnl_pct": 12.3,
            "max_drawdown": 5.2,
            "win_rate": 61.5,
            "profit_factor": 1.8,
            "total_trades": 27,
            "sharpe_ratio": 1.2
        }
    """
    # ------------------------------------------------------------------
    # Validate required fields
    # ------------------------------------------------------------------
    if not symbol:
        raise HTTPException(status_code=400, detail="Missing required query parameter: symbol")
    if not start_date:
        raise HTTPException(status_code=400, detail="Missing required query parameter: start_date")
    if not end_date:
        raise HTTPException(status_code=400, detail="Missing required query parameter: end_date")

    # Build the period range string that backtest_engine expects
    # Calculate period based on date difference
    date_format = "%Y-%m-%d"
    try:
        start_dt = datetime.strptime(start_date, date_format)
        end_dt = datetime.strptime(end_date, date_format)
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

    # Build strategy parameters dict
    strategy_params = {
        "risk_pct": risk_pct,
        "entry_score": entry_score,
        "stop_atr": stop_atr,
        "target_atr": target_atr,
        "early_exit": early_exit,
        "adx_min": adx_min,
        "initial_capital": initial_capital,
    }

    try:
        # Run the backtest using the engine
        config = BacktestConfig(period_range=period_range, **strategy_params)
        result = run_historical_backtest(symbol, config)
    except Exception as exc:
        # Propagate engine errors as 500s
        raise HTTPException(status_code=500, detail=str(exc))

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # ------------------------------------------------------------------
    # Calculate Sharpe ratio from equity curve (annualized)
    # ------------------------------------------------------------------
    sharpe_ratio = 0.0
    equity_curve = result.get("equity_curve", [])
    if len(equity_curve) > 1:
        # Calculate daily returns
        returns = []
        for i in range(1, len(equity_curve)):
            prev_val = equity_curve[i-1]["value"]
            curr_val = equity_curve[i]["value"]
            if prev_val != 0:  # Avoid division by zero
                daily_return = (curr_val - prev_val) / prev_val
                returns.append(daily_return)

        if returns:
            # Calculate Sharpe ratio: (mean return / std dev) * sqrt(252)
            mean_return = sum(returns) / len(returns)
            # Calculate variance
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            if variance > 0:
                std_return = variance ** 0.5
                sharpe_ratio = round((mean_return / std_return) * (252 ** 0.5), 2)

    # ------------------------------------------------------------------
    # Package metrics for the frontend
    # ------------------------------------------------------------------
    metrics = {
        "total_pnl_pct": result["total_pnl_pct"],
        "max_drawdown": result["max_drawdown"],
        "win_rate": result["win_rate"],
        "profit_factor": result["profit_factor"],
        "total_trades": result["total_trades"],
        "sharpe_ratio": sharpe_ratio,
        "final_capital": result.get("final_capital", initial_capital),
    }

    return metrics


# ----------------------------------------------------------------------
# Default route (optional)
# ----------------------------------------------------------------------
@app.get("/", tags=["root"])
async def read_root():
    return {"status": "ok", "message": "ApexTrade API – backtest endpoint available at /api/backtest/run"}
