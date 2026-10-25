"""Test suite configuration — enables CSRF bypass globally so existing tests
don't break. Tests that verify CSRF enforcement (test_csrf.py) unset TESTING
env var before their requests."""
import pytest
import os

# Set TESTING env var to disable CSRF for all tests.
# Tests that need to verify CSRF enforcement unset this before making requests.
os.environ["TESTING"] = "1"
# Explicitly disable background workers for test suite
os.environ["SKIP_BACKGROUND_WORKERS"] = "true"


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """Initialize database tables before running tests."""
    from app.core.database import init_db
    init_db()


@pytest.fixture(autouse=True)
def _disable_csrf_bypass():
    """Ensure TESTING=1 is set for CSRF bypass during tests."""
    os.environ["TESTING"] = "1"
    os.environ["SKIP_BACKGROUND_WORKERS"] = "true"
    yield
    os.environ["TESTING"] = "1"  # Reset after each test
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
    """TestClient with a valid apt_token cookie for authenticated requests."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    
    client = TestClient(app)
    token = create_access_token({"sub": "apex_head_quant"})
    client.cookies.set("apt_token", token)
    return client
