"""Tests for fail-loud worker startup and skip_background_workers configuration."""
import asyncio
from unittest.mock import patch
import pytest
from app.main import app, lifespan, _attach_worker_monitor
from app.core.config import settings
from fastapi.testclient import TestClient


def test_lifespan_crashes_loudly_on_worker_startup_error():
    """Proves that when skip_background_workers is False, any worker startup failure raises immediately."""
    async def _run():
        original_skip = settings.skip_background_workers
        try:
            settings.skip_background_workers = False
            with patch("asyncio.create_task", side_effect=RuntimeError("Simulated broker/worker crash")):
                with pytest.raises(RuntimeError, match="Simulated broker/worker crash"):
                    async with lifespan(app):
                        pass
                assert app.state.worker_startup_failed == "Simulated broker/worker crash"
        finally:
            settings.skip_background_workers = original_skip

    asyncio.run(_run())


def test_lifespan_skips_workers_when_configured():
    """Proves that when skip_background_workers is True, workers are skipped cleanly without errors."""
    async def _run():
        original_skip = settings.skip_background_workers
        try:
            settings.skip_background_workers = True
            async with lifespan(app):
                assert app.state.agent_task is None
                assert app.state.resolver_task is None
                assert app.state.governance_task is None
        finally:
            settings.skip_background_workers = original_skip

    asyncio.run(_run())


def test_worker_monitor_records_crashed_worker():
    """Proves that a task raising an exception is recorded in app.state.degraded_workers."""
    async def _run():
        # Ensure clean state
        if hasattr(app.state, "degraded_workers"):
            del app.state.degraded_workers

        async def failing_task():
            await asyncio.sleep(0.01)
            raise RuntimeError("worker crashed")

        task = asyncio.create_task(failing_task())
        _attach_worker_monitor(app, task, "test_failing_worker")

        with pytest.raises(RuntimeError, match="worker crashed"):
            await task

        # Wait for callback to execute
        await asyncio.sleep(0.01)

        assert hasattr(app.state, "degraded_workers")
        assert "test_failing_worker" in app.state.degraded_workers
        assert "worker crashed" in app.state.degraded_workers["test_failing_worker"]

    asyncio.run(_run())


def test_worker_monitor_ignores_cancelled_task():
    """Proves that a cancelled task does NOT appear in degraded_workers."""
    async def _run():
        # Ensure clean state
        if hasattr(app.state, "degraded_workers"):
            del app.state.degraded_workers

        async def long_task():
            await asyncio.sleep(10)  # Never completes

        task = asyncio.create_task(long_task())
        _attach_worker_monitor(app, task, "test_cancelled_worker")

        # Cancel immediately
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Wait for callback to execute
        await asyncio.sleep(0.01)

        # Cancelled tasks must not be recorded
        degraded = getattr(app.state, "degraded_workers", {})
        assert "test_cancelled_worker" not in degraded

    asyncio.run(_run())


def test_worker_status_reflects_degraded_workers():
    """Proves /api/admin/worker-status shows degraded=true and agent_running=false when degraded_workers is set."""
    # Ensure clean state
    if hasattr(app.state, "degraded_workers"):
        del app.state.degraded_workers

    # Inject a degraded worker
    app.state.degraded_workers = {"test_worker": "simulated crash"}

    # Get admin key from settings
    from app.core.config import settings
    admin_key = settings.admin_key

    client = TestClient(app)
    r = client.get("/api/admin/worker-status", headers={"X-Admin-Key": admin_key})

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["degraded"] is True
    assert data["agent_running"] is False
    assert "test_worker" in data["degraded_workers"]