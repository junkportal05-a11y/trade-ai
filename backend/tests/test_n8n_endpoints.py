"""Unit tests for all 4 n8n / agent webhook endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.models import PredictionsHistory
from app.api.deps import get_db

client = TestClient(app)


def test_kill_switch_check():
    with patch("app.api.v1.n8n.check_risk_limits", return_value={"triggered": False, "reason": "safe", "daily_loss_pct": -1.2, "drawdown_pct": -2.1}):
        res = client.get("/api/n8n/kill-switch-check")
        assert res.status_code == 200
        data = res.json()
        assert data["triggered"] is False
        assert data["daily_loss_pct"] == -1.2
        assert data["drawdown_pct"] == -2.1
        assert "daily_limit_pct" in data


def test_data_integrity_check():
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 0
    mock_session.query.return_value = mock_query

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        with patch("data_validator.calculate_data_confidence", return_value={"confidence_score": 95.0}):
            res = client.get("/api/n8n/data-integrity-check")
            assert res.status_code == 200
            data = res.json()
            assert data["confidence_score"] == 95.0
            assert data["missing_trades"] == 0
            assert data["alert_needed"] is False
    finally:
        app.dependency_overrides.clear()


def test_metrics_no_trades():
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = []
    mock_session.query.return_value = mock_query

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        res = client.get("/api/n8n/metrics")
        assert res.status_code == 200
        data = res.json()
        assert data["total_trades"] == 0
        assert data["profit_factor"] is None
        assert data["win_rate"] is None
    finally:
        app.dependency_overrides.clear()


def test_metrics_with_resolved_trades():
    trade1 = MagicMock()
    trade1.status = "WIN"
    trade1.pnl_inr = 1500.0
    trade1.pnl_pct = 3.0
    trade1.actual_outcome = "TARGET_HIT"

    trade2 = MagicMock()
    trade2.status = "LOSS"
    trade2.pnl_inr = -500.0
    trade2.pnl_pct = -1.0
    trade2.actual_outcome = "STOP_HIT"

    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [trade1, trade2]
    mock_session.query.return_value = mock_query

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        res = client.get("/api/n8n/metrics")
        assert res.status_code == 200
        data = res.json()
        assert data["total_trades"] == 2
        assert data["win_rate"] == 0.5
        assert data["profit_factor"] == 3.0
        assert data["ev_pct"] == 1.0
    finally:
        app.dependency_overrides.clear()


def test_trigger_scan_endpoints():
    with patch("trading_agent.run_scan_cycle", return_value=[{"symbol": "TCS.NS", "signal": "BUY"}]):
        # Test /api/n8n/trigger-scan
        res1 = client.post("/api/n8n/trigger-scan")
        assert res1.status_code == 200
        assert res1.json()["status"] == "scan_completed"
        assert res1.json()["signals_found"] == 1

        # Test /api/agent/trigger-scan
        res2 = client.post("/api/agent/trigger-scan")
        assert res2.status_code == 200
        assert res2.json()["status"] == "scan_completed"
        assert res2.json()["signals_found"] == 1
