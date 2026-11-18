"""FastAPI application entry point."""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.core.config import settings
from app.models.schemas import BacktestRequest
from app.core.database import init_db
from app.core.logging import configure_json_logging, logger, set_correlation_id, get_correlation_id
from app.core.security import get_token_from_request
from app.core.worker_state import set_degraded_worker, clear_all_degraded_workers

from datetime import datetime
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

def _attach_worker_monitor(app: FastAPI, task: asyncio.Task, name: str):
    """Attach a done callback to detect unexpected worker termination."""
    def _on_done(t: asyncio.Task):
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.critical(f"CRITICAL: Background worker '{name}' crashed: {exc}", exc_info=exc)
            set_degraded_worker(name, str(exc))
        else:
            logger.critical(f"CRITICAL: Background worker '{name}' exited unexpectedly with no exception.")
            set_degraded_worker(name, "exited with no exception")
    task.add_done_callback(_on_done)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    init_db()
    clear_all_degraded_workers()

    # Initialize worker task references to None explicitly
    app.state.agent_task = None
    app.state.resolver_task = None
    app.state.governance_task = None

    # Skip background workers if explicitly configured (e.g., in serverless/Cloud Run web instances)
    enable_workers = os.getenv("ENABLE_BACKGROUND_WORKERS", "false").lower() == "true"
    if not enable_workers:
        logger.info("Background workers disabled (ENABLE_BACKGROUND_WORKERS=false)")
    elif settings.skip_background_workers:
        logger.info("Background workers skipped (SKIP_BACKGROUND_WORKERS=true)")
    else:
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
                resolver_task = asyncio.create_task(prediction_resolver_worker())
                app.state.resolver_task = resolver_task
                _attach_worker_monitor(app, resolver_task, "prediction_resolver_worker")

            # Start the loop as a background asyncio task
            agent_task = asyncio.create_task(trading_agent_loop())
            app.state.agent_task = agent_task
            _attach_worker_monitor(app, agent_task, "trading_agent_loop")
            logger.info("trading_agent_loop task created")

            if hasattr(governance_worker, "governance_loop"):
                governance_task = asyncio.create_task(governance_worker.governance_loop())
                app.state.governance_task = governance_task
                _attach_worker_monitor(app, governance_task, "governance_loop")
        except Exception as exc:
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
                if task:
                    task.cancel()
                    await task
            except asyncio.CancelledError:
                pass

# Debug is a development-only affordance; the standard OpenAPI docs are
# disabled entirely in production so the public API surface can't be enumerated.
_is_production = settings.environment == "production"
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug and settings.environment == "development",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    lifespan=lifespan,
)
trusted_hosts = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "127.0.0.1").split(",") if h.strip()]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_hosts)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize Sentry error tracing if DSN is configured
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        environment=settings.environment,
    )
    logger.info("Sentry error tracing initialized")

# CORS
# Use ALLOWED_ORIGINS env var (comma-separated) to override the hardcoded default
allowed = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
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


# ── Generic fallback exception handler ───────────────────────────────────
# Any unhandled exception returns a generic error shape (never a traceback,
# never internal details) plus the correlation id for log-server joining.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        extra={"method": request.method, "path": request.url.path, "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "correlation_id": get_correlation_id() or str(uuid.uuid4()),
        },
    )

# API routes
from app.api.v1 import api_router
app.include_router(api_router)

# Serve static files for graphify output
graph_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "graphify-out"))
os.makedirs(graph_dir, exist_ok=True)
app.mount("/graphify-out", StaticFiles(directory=graph_dir), name="graphify-out")

# ----------------------------------------------------------------------
# Backtest engine handler (route registration lives in app/api/v1/backtest.py;
# this module previously re-declared POST /api/backtest/run as a dead shadow
# of the v1 router — removed to avoid duplicate routes). The rate limiting and
# auth deps live on the v1 route.
# ----------------------------------------------------------------------
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
        # Full details are logged server-side; the public message stays generic
        # so engine/exception internals never reach the client.
        logger.error(f"Backtest execution error for {sym}: {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail="Backtest failed: invalid parameters or insufficient data")

    if isinstance(result, dict) and "error" in result:
        logger.error(f"Backtest engine error for {sym}: {result['error']}")
        raise HTTPException(status_code=400, detail="Backtest failed: invalid parameters or insufficient data")

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
# (GET /api/quote was removed — it duplicated app/api/v1/quotes.py's route,
# which is the registered router-level definition; main.py's copy was a
# dead shadow that never served traffic.)
@app.get("/", tags=["root"])
async def read_root():
    return {"status": "ok", "message": """ApexTrade AI Core Backend Engine.
"""}