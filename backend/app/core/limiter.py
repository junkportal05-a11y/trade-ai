"""SlowAPI Limiter core module with Redis/Upstash support and in-memory fallback."""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from app.core.config import settings


def get_real_client_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


def _get_storage_uri() -> str:
    """Determine storage URI: Redis (Upstash) if configured, else in-memory."""
    redis_url = settings.effective_redis_url
    if redis_url:
        return redis_url
    return "memory://"


# Initialize limiter with appropriate storage backend
storage_uri = _get_storage_uri()
limiter = Limiter(key_func=get_real_client_ip, default_limits=["120/minute"], storage_uri=storage_uri)
