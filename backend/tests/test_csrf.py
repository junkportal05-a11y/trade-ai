"""CSRF protection tests — verify X-Requested-With header enforcement."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_csrf_missing_header_rejected_on_mutating_routes(monkeypatch):
    """Mutating requests without X-Requested-With must get 403."""
    # Temporarily disable CSRF bypass for this test
    monkeypatch.delenv("TESTING", raising=False)
    # POST without the header
    response = client.post(
        "/api/scan",
        json={"symbol": "RELIANCE.NS"},
    )
    assert response.status_code == 403, (
        f"Expected 403 for missing CSRF header, got {response.status_code}: {response.json()}"
    )
    assert "csrf" in response.json().get("detail", "").lower()


def test_csrf_missing_header_rejected_on_bot_start(monkeypatch):
    """POST /api/bot/start without CSRF header returns 403."""
    monkeypatch.delenv("TESTING", raising=False)
    response = client.post("/api/bot/start")
    assert response.status_code == 403


def test_csrf_header_present_passes_through(monkeypatch):
    """Mutating requests with X-Requested-With header pass through."""
    monkeypatch.delenv("TESTING", raising=False)
    response = client.post(
        "/api/scan",
        json={"symbol": "RELIANCE.NS"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    # 200/401/etc — should NOT be 403 from CSRF
    assert response.status_code != 403 or "csrf" not in response.json().get("detail", "").lower()


def test_get_requests_always_allowed():
    """GET requests bypass CSRF check regardless of header."""
    response = client.get("/")
    assert response.status_code == 200


def test_head_requests_always_allowed():
    """HEAD requests bypass CSRF check."""
    response = client.head("/")
    assert response.status_code in (200, 204, 405)


def test_options_requests_always_allowed():
    """OPTIONS requests bypass CSRF check."""
    response = client.options("/")
    # OPTIONS may return 405 (method not allowed) but not 403 from CSRF
    assert response.status_code != 403 or "csrf" not in response.json().get("detail", "").lower()


def _cookie_client(csrf_cookie: str | None = None, csrf_header: str | None = None) -> TestClient:
    from app.core.security import create_access_token

    headers = {"X-Requested-With": "XMLHttpRequest"}
    if csrf_header is not None:
        headers["X-CSRF-Token"] = csrf_header
    c = TestClient(app, headers=headers)
    c.cookies.set("apt_token", create_access_token({"sub": "csrf_probe"}))
    if csrf_cookie is not None:
        c.cookies.set("apt_csrf", csrf_cookie)
    return c


def test_cookie_session_without_csrf_token_rejected():
    """A cookie session must not rely on X-Requested-With alone."""
    c = _cookie_client()
    response = c.post("/api/scan", json={"symbol": "RELIANCE.NS"})
    assert response.status_code == 403
    assert "csrf" in response.json().get("detail", "").lower()


def test_cookie_session_with_matching_csrf_token_passes():
    c = _cookie_client(csrf_cookie="csrf-value", csrf_header="csrf-value")
    response = c.post("/api/scan", json={"symbol": "RELIANCE.NS"})
    assert response.status_code != 403 or "csrf" not in response.json().get("detail", "").lower()


def test_cookie_session_with_mismatched_csrf_token_rejected():
    c = _cookie_client(csrf_cookie="csrf-value", csrf_header="other-value")
    response = c.post("/api/scan", json={"symbol": "RELIANCE.NS"})
    assert response.status_code == 403
    assert "csrf" in response.json().get("detail", "").lower()
