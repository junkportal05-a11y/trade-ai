"""Central thread pool executors for background workers.

Each background worker type gets its own dedicated, independently-sized executor
to prevent contention between different workload categories.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import atexit

# ── Scan executor (signal scanning, batch analysis) ─────────────────────────
# CPU-bound indicator calculations + I/O for market data
scan_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scan-")

# ── Quote executor (live quote fetches, WebSocket handlers) ────────────────
# I/O-bound, mostly waiting on broker API
quote_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="quote-")

# ── Governance executor (risk limits, kill switches) ───────────────────────
# Lightweight periodic checks
governance_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="governance-")

# ── Trading executor (order placement, position management) ─────────────────
# Mixed I/O + light compute
trading_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="trading-")

# ── Resolver executor (SL/TP resolution, position reconciliation) ───────────
# I/O-bound, frequent broker API calls
resolver_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="resolver-")


# ── Cleanup on shutdown ────────────────────────────────────────────────────
def shutdown_executors() -> None:
    """Gracefully shutdown all executors on process exit."""
    for name, executor in [
        ("scan", scan_executor),
        ("quote", quote_executor),
        ("governance", governance_executor),
        ("trading", trading_executor),
        ("resolver", resolver_executor),
    ]:
        try:
            executor.shutdown(wait=True)
        except Exception:
            # Best effort - log and continue
            pass


atexit.register(shutdown_executors)