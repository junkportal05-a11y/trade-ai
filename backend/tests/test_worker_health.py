"""Unit tests for Prompt 2: Worker health heartbeats and /api/n8n/status monitoring endpoint."""
import os
import pytest
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

def test_n8n_status_endpoint_returns_workers():
    # Emit heartbeats
    beat("agent")
    beat("resolver")

    response = client.get("/api/n8n/status")
    assert response.status_code == 200
    data = response.json()

    assert "workers" in data
    workers = data["workers"]
    assert "agent" in workers
    assert "resolver" in workers
    assert workers["agent"]["status"] == "healthy"
    assert workers["resolver"]["status"] == "healthy"
