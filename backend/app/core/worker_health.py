"""Shared worker heartbeat registry for per-worker health checks."""
from __future__ import annotations

import time
from threading import Lock

_heartbeats: dict[str, float] = {}
_lock = Lock()
STALE_THRESHOLD_SECONDS = 120  # 2 minutes

def beat(worker_name: str) -> None:
    """Record a heartbeat for a worker."""
    with _lock:
        _heartbeats[worker_name] = time.monotonic()

def get_all() -> dict[str, dict]:
    """Return status of all registered workers."""
    now = time.monotonic()
    with _lock:
        result = {}
        for name, last in _heartbeats.items():
            age = now - last
            result[name] = {
                "last_beat_seconds_ago": round(age, 1),
                "status": "healthy" if age < STALE_THRESHOLD_SECONDS else "stale",
            }
        return result