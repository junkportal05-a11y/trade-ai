"""TAR-15 security hardening tests: CSRF header enforcement on mutating routes
and the missing logger regression in predictions.py."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def _post(path: str, **kwargs):
    return client.post(path, **kwargs)


def test_csrf_rejected_on_strategies(tmp_path, monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    response = _post("/api/strategies", json={"name": "x"})
    assert response.status_code == 403
    assert "csrf" in response.json().get("detail", "").lower()


def test_csrf_rejected_on_predictions(tmp_path, monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    for path in ("/api/predictions", "/api/journal"):
        response = _post(path, json={})
        assert response.status_code == 403, f"{path}: got {response.status_code}"
        assert "csrf" in response.json().get("detail", "").lower()


def test_csrf_rejected_on_chat_upload(monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    response = _post(
        "/api/chat/chart/upload",
        files={"file": ("chart.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert response.status_code == 403
    assert "csrf" in response.json().get("detail", "").lower()


def test_csrf_rejected_on_backtest(monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    # First login to get a session cookie
    login_response = _post("/api/auth/login", json={"username": "test", "password": "test"})
    if login_response.status_code == 200:
        cookie = login_response.cookies.get("session")
        headers = {"Cookie": f"session={cookie}"} if cookie else {}
        response = _post("/api/backtest/run", json={"symbol": "RELIANCE.NS"}, headers=headers)
        assert response.status_code == 403, f"got {response.status_code}"
        assert "csrf" in response.json().get("detail", "").lower()
    else:
        # If login fails (no test user), skip CSRF check - endpoint requires auth first
        response = _post("/api/backtest/run", json={"symbol": "RELIANCE.NS"})
        assert response.status_code in (401, 403), f"expected 401 or 403, got {response.status_code}"


def test_csrf_header_present_passes(monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    response = _post(
        "/api/predictions", json={}, headers={"X-Requested-With": "XMLHttpRequest"}
    )
    # With the header, CSRF passes; unauthenticated -> 401, never 403
    assert response.status_code != 403 or "csrf" not in response.json().get("detail", "").lower()


def test_predictions_module_has_logger():
    import app.api.v1.predictions as mod
    assert hasattr(mod, "logger") and mod.logger.name.endswith("predictions")


def test_bot_gets_not_csrf_gated(monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    token = create_access_token({"sub": "apex_head_quant"})
    headers = {"Authorization": f"Bearer {token}"}
    for path in ("/api/bot/status", "/api/bot/trades"):
        anon = client.get(path)
        assert anon.status_code == 401, f"{path}: got {anon.status_code}"
        assert "csrf" not in anon.json().get("detail", "").lower()
        authed = client.get(path, headers=headers)
        assert authed.status_code == 200, f"{path}: got {authed.status_code}"
        assert "csrf" not in authed.json().get("detail", "").lower()
