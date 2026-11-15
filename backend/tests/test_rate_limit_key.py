"""Rate-limit key derivation must not retain raw session tokens."""
from starlette.requests import Request

from app.api.deps import get_user_or_ip


def _request_with_token(token: str) -> Request:
    return Request({"type": "http", "headers": [(b"x-session-token", token.encode())]})


def test_rate_limit_key_hashes_session_token():
    key = get_user_or_ip(_request_with_token("raw-secret-token"))
    assert key.startswith("user:")
    assert "raw-secret-token" not in key
    assert key == get_user_or_ip(_request_with_token("raw-secret-token"))
    assert key != get_user_or_ip(_request_with_token("other-token"))
