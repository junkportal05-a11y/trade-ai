from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_ping():
    response = client.get("/api/health/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_health_ready():
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "database" in data
    assert "workers" in data


def test_health_deep_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "version" in data
    assert "checks" in data
    
    checks = data["checks"]
    assert "database" in checks
    assert "broker" in checks
    assert "ai_services" in checks
    assert "workers" in checks
    assert "storage" in checks
    assert "market" in checks
    assert checks["database"]["status"] in ("healthy", "unhealthy")
