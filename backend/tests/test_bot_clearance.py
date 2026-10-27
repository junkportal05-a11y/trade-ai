import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.security import require_session

client = TestClient(app)


def test_guest_cannot_start_or_pause_bot():
    app.dependency_overrides[require_session] = lambda: {"username": "guest_user", "role": "Guest", "clearance": "LEVEL_1_GUEST"}
    try:
        res_start = client.post("/api/bot/start")
        assert res_start.status_code == 403
        assert "Requires LEVEL_2_TRADER clearance" in res_start.json()["detail"]

        res_pause = client.post("/api/bot/pause")
        assert res_pause.status_code == 403
        assert "Requires LEVEL_2_TRADER clearance" in res_pause.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_trader_can_start_but_cannot_stop_bot():
    app.dependency_overrides[require_session] = lambda: {"username": "trader_user", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        with patch("db.set_bot_state"), patch("db.get_bot_state", return_value="RUNNING"):
            res_start = client.post("/api/bot/start")
            assert res_start.status_code == 200

        res_stop = client.post("/api/bot/stop")
        assert res_stop.status_code == 403
        assert "Requires LEVEL_3_ADMIN clearance" in res_stop.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_admin_can_stop_bot():
    app.dependency_overrides[require_session] = lambda: {"username": "admin_user", "role": "Admin", "clearance": "LEVEL_3_ADMIN"}
    try:
        with patch("db.set_bot_state"), patch("db.get_bot_state", return_value="STOPPED"), patch("trading_agent._square_off_all", new=AsyncMock()):
            res_stop = client.post("/api/bot/stop")
            assert res_stop.status_code == 200
            assert res_stop.json()["state"] == "STOPPED"
    finally:
        app.dependency_overrides.clear()