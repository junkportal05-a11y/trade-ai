"""Unit tests for multi-tenant journal ownership isolation."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.security import require_session
from app.core.database import Base, get_db

# Use an isolated in-memory SQLite database for unit tests
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app, headers={"X-Requested-With": "XMLHttpRequest"})


def test_journal_user_isolation():
    app.dependency_overrides[get_db] = override_get_db

    # User A creates an entry
    app.dependency_overrides[require_session] = lambda: {"username": "user_a", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        post_res = client.post("/api/journal", json={
            "symbol": "TCS.NS",
            "direction": "BUY",
            "entry_price": 3500.0,
            "qty": 10
        })
        assert post_res.status_code == 200
        entry_id = post_res.json()["id"]

        get_res_a = client.get("/api/journal")
        assert get_res_a.status_code == 200
        assert any(e["id"] == entry_id for e in get_res_a.json())
    finally:
        pass

    # User B should NOT see User A's entry and cannot delete it
    app.dependency_overrides[require_session] = lambda: {"username": "user_b", "role": "Trader", "clearance": "LEVEL_2_TRADER"}
    try:
        get_res_b = client.get("/api/journal")
        assert get_res_b.status_code == 200
        assert not any(e["id"] == entry_id for e in get_res_b.json())

        del_res = client.delete(f"/api/journal/{entry_id}")
        assert del_res.status_code == 404
    finally:
        app.dependency_overrides.clear()
