"""Unit tests for bot control endpoints auth enforcement & strategies router fix."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def test_bot_start_requires_auth():
    response = client.post("/api/bot/start")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_bot_pause_requires_auth():
    response = client.post("/api/bot/pause")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_bot_stop_requires_auth():
    response = client.post("/api/bot/stop")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_bot_status_requires_auth():
    response = client.get("/api/bot/status")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_bot_trades_requires_auth():
    response = client.get("/api/bot/trades")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_bot_status_with_valid_token():
    token = create_access_token({"sub": "apex_head_quant"})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/bot/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "today_pnl" in data


def test_get_strategy_by_id_no_name_error():
    response = client.get("/api/strategies/intraday_momentum")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "intraday_momentum"
