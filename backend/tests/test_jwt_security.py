"""JWT claim validation and server-side revocation tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    revoke_access_token,
)
from app.main import app


def test_access_token_carries_required_claims():
    token = create_access_token({"sub": "claims_user"})
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert payload["sub"] == "claims_user"
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience
    assert payload["jti"]
    assert payload["iat"]
    assert payload["exp"]


def test_token_with_wrong_audience_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "claims_user",
            "iss": settings.jwt_issuer,
            "aud": "someone-else",
            "jti": "wrong-aud-jti",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm=settings.algorithm,
    )
    assert decode_access_token(token) is None


def test_token_without_jti_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "claims_user",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm=settings.algorithm,
    )
    assert decode_access_token(token) is None


def test_revoked_token_is_rejected():
    token = create_access_token({"sub": "revoked_user"})
    assert decode_access_token(token) is not None

    assert revoke_access_token(token) is True
    assert decode_access_token(token) is None


def test_logout_revokes_access_token():
    token = create_access_token({"sub": "logout_user"})
    client = TestClient(
        app,
        headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-Token": "csrf-value"},
    )
    client.cookies.set("apt_token", token)
    client.cookies.set("apt_csrf", "csrf-value")

    response = client.post("/api/logout")
    assert response.status_code == 200, response.text
    assert decode_access_token(token) is None


def test_verify_rotates_missing_csrf_cookie():
    token = create_access_token({"sub": "verify_user"})
    client = TestClient(app)
    client.cookies.set("apt_token", token)

    response = client.get("/api/auth/verify")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["csrf_token"]
    assert client.cookies.get("apt_csrf") == body["csrf_token"]


def test_verify_rejects_revoked_cookie_session():
    token = create_access_token({"sub": "verify_revoked_user"})
    assert revoke_access_token(token) is True

    client = TestClient(app)
    client.cookies.set("apt_token", token)
    response = client.get("/api/auth/verify")
    assert response.status_code == 401
