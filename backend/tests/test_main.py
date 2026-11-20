from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root(auth_client):
    response = auth_client.get("/api/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Trading Platform API is running"}


def test_root_requires_auth():
    response = client.get("/api/")
    assert response.status_code == 401
