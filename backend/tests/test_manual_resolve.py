"""Unit tests for manual prediction resolution endpoint."""
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.core.security import require_session
from backend.app.main import app

client = TestClient(app)


def _mock_feed(exit_price: float, symbol: str):
    feed = MagicMock()
    feed.is_authorized.return_value = True
    feed.get_live_quotes.return_value = {symbol: {"price": exit_price}}
    return feed


def test_manual_resolve_manual_exit():
    """Test manual resolution with exit price between target and stop loss."""
    app.dependency_overrides[require_session] = lambda: {"username": "trader_user", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        pred_data = {
            "symbol": "RELIANCE.NS",
            "prediction_type": "BULLISH",
            "entry_price": 100.0,
            "target_price": 110.0,
            "stop_loss": 90.0,
            "confidence_score": 80,
        }
        response = client.post("/api/predictions", json=pred_data)
        assert response.status_code == 200, f"Failed to create prediction: {response.text}"
        pred_id = response.json()["id"]

        mock_feed = _mock_feed(95.0, "RELIANCE.NS")
        with patch("app.api.v1.predictions.get_broker_feed", return_value=mock_feed, create=True):
            response = client.post(f"/api/predictions/{pred_id}/resolve", json={
                "actual_outcome": "MANUAL_EXIT",
                "exit_price": 95.0,
                "manual_override_reason": "Manual override for testing",
                "notes": "test resolution",
            })
        assert response.status_code == 200, f"Failed to resolve prediction: {response.text}"
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["actual_outcome"] == "MANUAL_EXIT"
        assert data["exit_price"] == 95.0
    finally:
        app.dependency_overrides.clear()


def test_manual_resolve_target_hit():
    """Test manual resolution with exit price at or above target price."""
    app.dependency_overrides[require_session] = lambda: {"username": "trader_user", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        pred_data = {
            "symbol": "TCS.NS",
            "prediction_type": "BULLISH",
            "entry_price": 200.0,
            "target_price": 250.0,
            "stop_loss": 180.0,
            "confidence_score": 90,
        }
        response = client.post("/api/predictions", json=pred_data)
        assert response.status_code == 200, f"Failed to create prediction: {response.text}"
        pred_id = response.json()["id"]

        mock_feed = _mock_feed(250.0, "TCS.NS")
        with patch("app.api.v1.predictions.get_broker_feed", return_value=mock_feed, create=True):
            response = client.post(f"/api/predictions/{pred_id}/resolve", json={
                "actual_outcome": "TARGET_HIT",
                "exit_price": 250.0,
                "manual_override_reason": "Manual override for testing",
                "notes": "test resolution",
            })
        assert response.status_code == 200, f"Failed to resolve prediction: {response.text}"
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["actual_outcome"] == "TARGET_HIT"
        assert data["exit_price"] == 250.0
    finally:
        app.dependency_overrides.clear()


def test_manual_resolve_rejects_exit_price_mismatch():
    """exit_price far from live quote must be rejected by the broker cross-check.
    Stop-distance-scaled tolerance on a 100/110/90 setup: stop distance = 10,
    tolerance = (10/100)*100 = 10% of entry = ±10. Reported 60 is way outside.
    """
    app.dependency_overrides[require_session] = lambda: {"username": "trader_user", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        pred_data = {
            "symbol": "INFY.NS",
            "prediction_type": "BULLISH",
            "entry_price": 100.0,
            "target_price": 110.0,
            "stop_loss": 90.0,
            "confidence_score": 80,
        }
        response = client.post("/api/predictions", json=pred_data)
        assert response.status_code == 200, f"Failed to create prediction: {response.text}"
        pred_id = response.json()["id"]

        mock_feed = _mock_feed(105.0, "INFY.NS")
        with patch("app.api.v1.predictions.get_broker_feed", return_value=mock_feed, create=True):
            response = client.post(f"/api/predictions/{pred_id}/resolve", json={
                "actual_outcome": "TARGET_HIT",
                "exit_price": 60.0,
                "manual_override_reason": "fabricated exit",
                "notes": "mismatch test",
            })
        assert response.status_code == 422, f"Expected 422 for live-quote mismatch, got {response.status_code}: {response.text}"
        body = response.json()
        assert "live quote" in body.get("detail", "").lower() or "tolerance" in body.get("detail", "").lower()
    finally:
        app.dependency_overrides.clear()


def test_manual_resolve_persists_pnl_r_holding():
    """Manual resolve must not leave PnL / R / holding null: it computes
    pnl_pct, pnl_inr, r_multiple and holding_time_minutes from entry/stop/exit
    (position size defaults to 1 when the row carries none)."""
    app.dependency_overrides[require_session] = lambda: {"username": "trader_user", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        pred_data = {
            "symbol": "WIPRO.NS",
            "prediction_type": "BULLISH",
            "entry_price": 100.0,
            "target_price": 110.0,
            "stop_loss": 90.0,
            "confidence_score": 80,
        }
        response = client.post("/api/predictions", json=pred_data)
        assert response.status_code == 200, f"Failed to create prediction: {response.text}"
        pred_id = response.json()["id"]

        mock_feed = _mock_feed(105.0, "WIPRO.NS")
        with patch("app.api.v1.predictions.get_broker_feed", return_value=mock_feed, create=True):
            response = client.post(f"/api/predictions/{pred_id}/resolve", json={
                "actual_outcome": "MANUAL_EXIT",
                "exit_price": 105.0,
                "manual_override_reason": "manual exit mid-range",
                "notes": "metrics test",
            })
        assert response.status_code == 200, f"Failed to resolve prediction: {response.text}"
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["actual_outcome"] == "MANUAL_EXIT"
        # pnl_pct = (105 - 100) / 100 * 100 = 5
        assert data["pnl_pct"] == 5.0
        # pnl_inr = (105 - 100) * 1 = 5 (qty defaults to 1)
        assert data["pnl_inr"] == 5.0
        # r_multiple = (105 - 100) / |100 - 90| = 5 / 10 = 0.5
        assert data["r_multiple"] == 0.5
        assert data["holding_time_minutes"] >= 0

        from app.core.database import SessionLocal
        from app.db.models import PredictionsHistory
        with SessionLocal() as db:
            row = db.query(PredictionsHistory).filter(PredictionsHistory.id == pred_id).first()
            assert row is not None
            assert row.status == "RESOLVED"
            assert row.pnl_pct == 5.0
            assert row.pnl_inr == 5.0
            assert row.r_multiple == 0.5
            assert row.holding_time_minutes is not None
            assert row.holding_time_minutes >= 0
            assert row.resolution_reason == "manual exit mid-range"
    finally:
        app.dependency_overrides.clear()
