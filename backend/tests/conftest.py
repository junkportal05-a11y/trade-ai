"""Test suite configuration — TESTING=1 bypass removed; each test unsets it via monkeypatch.delenv()."""
import os
import tempfile

import pytest

# ── Database isolation (must run before ANY app/db import) ──────────────────
# Tests used to run against the real trading_platform.db, letting endpoint
# tests leak data into production (e.g. the test_key/jwt456 AngelOne session
# that poisoned startup). Point the whole suite at a throwaway SQLite file:
# empty DATABASE_URL forces app.core.database's SQLite fallback, and DB_PATH
# selects the temp file instead of the repo-root database.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="apextrade-test-db-")
os.environ["DATABASE_URL"] = ""
os.environ["DB_PATH"] = os.path.join(_TEST_DB_DIR, "test_trading_platform.db")

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

    CSRF is enforced unconditionally on mutating routes (TAR-21); cookie
    sessions must also present the apt_csrf double-submit pair.
    Tests asserting the missing-header 403 build their own bare clients.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token

    client = TestClient(
        app,
        headers={"X-Requested-With": "XMLHttpRequest", "X-CSRF-Token": "test-csrf"},
    )
    token = create_access_token({"sub": "apex_head_quant"})
    client.cookies.set("apt_token", token)
    client.cookies.set("apt_csrf", "test-csrf")
    return client