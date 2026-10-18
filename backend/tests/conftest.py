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
