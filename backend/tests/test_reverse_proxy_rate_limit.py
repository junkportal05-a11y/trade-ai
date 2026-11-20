"""Unit tests for rate limiter client IP extraction.

Deployment topology: docker-compose binds uvicorn directly (0.0.0.0:8000, no reverse
proxy in front). X-Forwarded-For / X-Real-IP are therefore attacker-controlled headers,
not trust signals. get_real_client_ip must ignore both and fall back to request.client.host,
which is the TCP peer address assigned by the kernel.
"""
from unittest.mock import MagicMock

from app.core.limiter import get_real_client_ip


def test_get_real_client_ip_ignores_x_forwarded_for_spoofing():
    # Attacker-controlled header must NOT override the real TCP peer.
    request = MagicMock()
    request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    request.client.host = "127.0.0.1"

    ip = get_real_client_ip(request)
    assert ip == "127.0.0.1"


def test_get_real_client_ip_ignores_x_real_ip():
    request = MagicMock()
    request.headers = {"X-Real-IP": "198.51.100.42"}
    request.client.host = "10.0.0.1"

    ip = get_real_client_ip(request)
    assert ip == "10.0.0.1"


def test_get_real_client_ip_fallback_to_client_host():
    request = MagicMock()
    request.headers = {}
    request.client.host = "192.168.1.50"

    ip = get_real_client_ip(request)
    assert ip == "192.168.1.50"


def test_get_real_client_ip_no_client_returns_loopback():
    request = MagicMock()
    request.headers = {}
    request.client = None

    ip = get_real_client_ip(request)
    assert ip == "127.0.0.1"