"""Shared worker state for cross-task communication of degraded workers."""
from __future__ import annotations

from threading import Lock

_degraded_workers: dict[str, str] = {}
_lock = Lock()


def get_degraded_workers() -> dict[str, str]:
    """Return a copy of the current degraded workers dict."""
    with _lock:
        return dict(_degraded_workers)


def set_degraded_worker(name: str, reason: str) -> None:
    """Record a worker as degraded."""
    with _lock:
        _degraded_workers[name] = reason


def clear_degraded_worker(name: str) -> None:
    """Clear a worker from degraded state (e.g., on recovery)."""
    with _lock:
        _degraded_workers.pop(name, None)


def clear_all_degraded_workers() -> None:
    """Clear all degraded workers."""
    with _lock:
        _degraded_workers.clear()


def any_degraded() -> bool:
    """Check if any worker is currently degraded."""
    with _lock:
        return bool(_degraded_workers)