from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.core.config import settings

client = TestClient(app)


@patch("app.db.repositories.SignalRepository.get_stats")
def test_admin_health_success(mock_get_stats):
    mock_get_stats.return_value = {"total": 10, "active": 2}
    response = client.get(f"/api/admin/health?x_admin_key={settings.admin_key}")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "signals_stats": {"total": 10, "active": 2},
    }


@patch("app.db.repositories.SignalRepository.get_stats")
def test_admin_health_missing_key(mock_get_stats):
    response = client.get("/api/admin/health")
    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}


@patch("app.db.repositories.SignalRepository.get_stats")
def test_admin_health_invalid_key(mock_get_stats):
    response = client.get("/api/admin/health?x_admin_key=invalid_key")
    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}
