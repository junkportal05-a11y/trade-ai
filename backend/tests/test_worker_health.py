"""Unit tests for worker health heartbeats."""
from fastapi.testclient import TestClient

from app.core.worker_health import beat, get_all, STALE_THRESHOLD_SECONDS
from app.main import app

client = TestClient(app)

def test_worker_health_heartbeat_registration():
    # Emit heartbeats for agent and resolver
    beat("agent")
    beat("resolver")

    health = get_all()
    assert "agent" in health
    assert "resolver" in health

    assert health["agent"]["status"] == "healthy"
    assert health["agent"]["last_beat_seconds_ago"] < STALE_THRESHOLD_SECONDS

    assert health["resolver"]["status"] == "healthy"
    assert health["resolver"]["last_beat_seconds_ago"] < STALE_THRESHOLD_SECONDS
