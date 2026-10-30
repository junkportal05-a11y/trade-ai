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


async def _test_csrf_protect_wrapper(request: pytest.importorskip("fastapi").Request):
    """CSRF test wrapper in conftest — delegates to real csrf_protect when TESTING env is deleted."""
    from app.core.security import csrf_protect
    if not os.getenv("TESTING"):
        return await csrf_protect(request)
    return True


@pytest.fixture(autouse=True)
def _disable_csrf_bypass():
    """Ensure TESTING=1 is set for CSRF bypass during tests via dependency override."""
    from app.main import app
    from app.core.security import csrf_protect

    app.dependency_overrides[csrf_protect] = _test_csrf_protect_wrapper
    os.environ["TESTING"] = "1"
    os.environ["SKIP_BACKGROUND_WORKERS"] = "true"
    yield
    app.dependency_overrides.pop(csrf_protect, None)
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
def client():
    """TestClient with CSRF header pre-set for test requests."""
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    c.headers["X-Requested-With"] = "XMLHttpRequest"
    return c


@pytest.fixture
def auth_client():
    """TestClient with a valid apt_token cookie and CSRF header for authenticated requests."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token

    c = TestClient(app)
    token = create_access_token({"sub": "apex_head_quant"})
    c.cookies.set("apt_token", token)
    c.headers["X-Requested-With"] = "XMLHttpRequest"
    return c
