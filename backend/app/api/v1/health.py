"""Health check endpoints for pre-flight diagnostics and runtime monitoring."""
from __future__ import annotations

import os
import shutil
import time
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import engine, get_pool_status
from app.core.worker_state import get_degraded_workers, any_degraded
from app.services.market_hours import is_nse_market_open

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


def check_database() -> dict[str, Any]:
    """Test database connectivity and measure latency."""
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        db_type = "postgresql" if settings.is_postgres else "sqlite"

        # Get pool status for PostgreSQL
        pool_info = {}
        if settings.is_postgres:
            pool_info = get_pool_status()

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "type": db_type,
            "pool": pool_info,
        }
    except OperationalError as e:
        logger.error("Database health check failed (OperationalError): %s", e)
        return {
            "status": "unhealthy",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "error": "database connection failed",
        }
    except Exception as e:
        logger.error("Database health check failed (unexpected): %s", e)
        return {
            "status": "unhealthy",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "error": "database check error",
        }


def check_broker() -> dict[str, Any]:
    """Validate Angel One credentials and trading mode."""
    has_credentials = all([
        settings.angel_api_key,
        settings.angel_client_code,
        settings.angel_pin,
        settings.angel_totp_secret,
    ])
    
    if not has_credentials:
        if settings.trading_mode == "paper":
            # Paper-only operation does not require a broker — informational, not a fault.
            return {
                "status": "paper_no_broker",
                "mode": settings.trading_mode,
                "live_armed": settings.live_trading_armed,
                "message": "Paper-only mode — broker credentials not configured (informational)",
            }
        return {
            "status": "not_configured",
            "mode": settings.trading_mode,
            "live_armed": settings.live_trading_armed,
            "message": "Angel One credentials not configured",
        }

    return {
        "status": "configured",
        "mode": settings.trading_mode,
        "live_armed": settings.live_trading_armed,
    }


def check_ai_services() -> dict[str, Any]:
    """Check AI service API key availability."""
    gemini_ok = bool(settings.gemini_api_key)
    news_ok = bool(settings.news_api_key)
    return {
        "status": "configured" if gemini_ok or news_ok else "not_configured",
        "gemini": {
            "configured": gemini_ok,
            "status": "configured" if gemini_ok else "not_configured",
        },
        "news_api": {
            "configured": news_ok,
            "status": "configured" if news_ok else "not_configured",
        },
    }


def check_workers() -> dict[str, Any]:
    """Check background worker health from worker_state."""
    worker_names = ["prediction_loop", "prediction_resolver_worker"]

    # Workers that were never started must never report "healthy".
    enable_workers = os.getenv("ENABLE_BACKGROUND_WORKERS", "false").lower() == "true"
    if not enable_workers or settings.skip_background_workers:
        return {
            "status": "disabled",
            "workers": {name: {"status": "disabled"} for name in worker_names},
            "degraded_count": 0,
        }

    degraded = get_degraded_workers()
    workers = {}
    for name in worker_names:
        if name in degraded:
            workers[name] = {"status": "degraded", "reason": degraded[name]}
        else:
            workers[name] = {"status": "healthy"}

    return {
        "status": "degraded" if any_degraded() else "healthy",
        "workers": workers,
        "degraded_count": len(degraded),
    }


def check_storage() -> dict[str, Any]:
    """Check disk space and data directory accessibility."""
    checks = {}
    
    # Root disk space
    try:
        total, used, free = shutil.disk_usage("/")
        free_gb = round(free / (1024**3), 2)
        total_gb = round(total / (1024**3), 2)
        checks["root_disk"] = {
            "status": "healthy" if free_gb > 1 else "warning",
            "free_gb": free_gb,
            "total_gb": total_gb,
            "usage_pct": round((used / total) * 100, 1),
        }
    except Exception as e:
        logger.error("Disk usage check failed: %s", e)
        checks["root_disk"] = {"status": "error", "error": "disk usage check failed"}

    # Knowledge directory (a missing data dir is a warning, not a degraded driver)
    knowledge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", settings.knowledge_dir))
    checks["knowledge_dir"] = {
        "status": "healthy" if os.path.exists(knowledge_path) else "warning",
        "exists": os.path.exists(knowledge_path),
    }

    # Historical data directory
    hist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", settings.historical_data_dir))
    checks["historical_data_dir"] = {
        "status": "healthy" if os.path.exists(hist_path) else "warning",
        "exists": os.path.exists(hist_path),
    }

    # Database file (for SQLite)
    if not settings.is_postgres:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", settings.db_path))
        checks["database_file"] = {
            "status": "healthy" if os.path.exists(db_path) else "warning",
            "exists": os.path.exists(db_path),
        }

    # Overall storage status
    statuses = [v.get("status", "unknown") for v in checks.values()]
    overall = "healthy"
    if any(s == "error" for s in statuses):
        overall = "error"
    elif any(s == "warning" for s in statuses):
        overall = "warning"

    return {"status": overall, "checks": checks}


def check_market_status() -> dict[str, Any]:
    """Check if NSE market is currently open."""
    datetime.now(timezone.utc)
    # Simple IST offset check
    is_open = is_nse_market_open()
    
    return {
        "status": "open" if is_open else "closed",
        "is_open": is_open,
        "timezone": "IST (UTC+5:30)",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    """Comprehensive health check endpoint."""
    start = time.perf_counter()
    
    # Run all checks
    db_check = check_database()
    broker_check = check_broker()
    ai_check = check_ai_services()
    workers_check = check_workers()
    storage_check = check_storage()
    market_check = check_market_status()
    
    checks = {
        "database": db_check,
        "broker": broker_check,
        "ai_services": ai_check,
        "workers": workers_check,
        "storage": storage_check,
        "market": market_check,
    }
    
    # Determine overall status
    # "paper_no_broker" is informational (paper mode needs no broker) and
    # "disabled" workers are a deliberate web-instance configuration — neither degrades health.
    statuses = [c.get("status", "unknown") for c in checks.values()]
    has_unhealthy = any(s in ("unhealthy", "error") for s in statuses)
    has_degraded = any(s == "degraded" for s in statuses)
    has_warning = any(s == "warning" for s in statuses)

    if has_unhealthy:
        overall = "unhealthy"
    elif has_degraded:
        overall = "degraded"
    elif has_warning:
        overall = "warning"
    else:
        overall = "healthy"
    
    total_latency_ms = round((time.perf_counter() - start) * 1000, 2)
    
    return {
        "status": overall,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": checks,
        "total_latency_ms": total_latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ping")
async def ping() -> dict[str, str]:
    """Lightweight ping endpoint for load balancers."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Kubernetes-style readiness probe - checks critical dependencies only."""
    db_check = check_database()
    workers_check = check_workers()
    
    ready = db_check.get("status") == "healthy" and workers_check.get("status") != "degraded"
    
    return {
        "ready": ready,
        "database": db_check.get("status"),
        "workers": workers_check.get("status"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }