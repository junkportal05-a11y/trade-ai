from fastapi.testclient import TestClient
from backend.main import app
import backend.main as main

client = TestClient(app)


def test_upstox_authorize_missing_env(monkeypatch):
    monkeypatch.setattr(main.upstox_feed, "UPSTOX_API_KEY", "")
    monkeypatch.setattr(main.upstox_feed, "UPSTOX_REDIRECT_URI", "")

    response = client.get("/api/upstox/authorize", follow_redirects=False)

    assert response.status_code == 400
    assert "Upstox API key or Redirect URI not configured" in response.json()["detail"]

def test_upstox_authorize_success(monkeypatch):
    monkeypatch.setattr(main.upstox_feed, "UPSTOX_API_KEY", "test_key")
    monkeypatch.setattr(main.upstox_feed, "UPSTOX_REDIRECT_URI", "http://localhost/callback")

    response = client.get("/api/upstox/authorize?state=test_state", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers.get("location")
    assert location is not None
    assert "client_id=test_key" in location
    assert "oauth_csrf_token" in response.cookies
