"""Test suite configuration — TESTING=1 bypass removed; each test unsets it via monkeypatch.delenv()."""
import pytest
import os

# Background workers explicitly disabled for test suite
os.environ["SKIP_BACKGROUND_WORKERS"] = "true"


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """Initialize database tables before running tests."""
    from app.core.database import init_db
    init_db()


@pytest.fixture(autouse=True)
def _disable_csrf_bypass():
    """Ensure TESTING=1 is NOT set globally; each test unsets it via monkeypatch.delenv()."""
    os.environ.pop("TESTING", None)
    os.environ["SKIP_BACKGROUND_WORKERS"] = "true"
    yield
    os.environ.pop("TESTING", None)
    os.environ["SKIP_BACKGROUND_WORKERS"] = "true"


@pytest.fixture(autouse=True)
def _clear_degraded_workers():
    """Clear degraded workers state before and after each test to prevent leakage."""
    from app.core.worker_state import clear_all_degraded_workers
    clear_all_degraded_workers()
    yield
    clear_all_degraded_workers()


@pytest.fixture
def auth_client():
    """TestClient with a valid apt_token cookie for authenticated requests.

    CSRF is enforced unconditionally on mutating routes (TAR-21), so send the
    same X-Requested-With header the real frontend's apiFetch always sends.
    Tests asserting the missing-header 403 build their own bare clients.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token

    client = TestClient(app, headers={"X-Requested-With": "XMLHttpRequest"})
    token = create_access_token({"sub": "apex_head_quant"})
    client.cookies.set("apt_token", token)
    return client