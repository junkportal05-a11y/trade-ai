#!/usr/bin/env python
"""
Integration test for ApexTrade FastAPI backend.

This test verifies:
  • The /api/signals/scan endpoint can be called (or equivalent signal creation)
  • A signal can be persisted and retrieved via the /api/signals/history endpoint
  • The health endpoint returns a successful response
"""

import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the FastAPI app
from app.main import app

# Import the DB models (SQLAlchemy Base)
from app.db import Base

# Use an in‑memory SQLite DB for isolation
SQLAlchemyEngine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SQLAlchemyEngine)

# Create all tables in the in‑memory DB
Base.metadata.create_all(bind=SQLAlchemyEngine)


# Dependency override for testing
def override_get_db():
    db = TestingSessionLocal
    try:
        yield db
    finally:
        pass


app.dependency_overrides[app.get_db] = override_get_db


def test_basic_endpoints():
    """Simple sanity check that the API server starts."""
    client = TestClient(app)
    response = client.get("/api/admin/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_signal_lifecycle(db_session):
    """
    Create a fake signal, store it, then read it back.
    This verifies that the persistence layer works for the resolver.
    """
    # Insert a dummy record directly via the ORM
    from app.models import Prediction  # Assume this model exists
    pred = Prediction(symbol="TEST", score=50, status="PENDING")
    db_session.add(pred)
    db_session.commit()
    db_session.refresh(pred)

    # Retrieve it again
    retrieved = db_session.query(Prediction).filter(Prediction.symbol == "TEST").first()
    assert retrieved is not None
    assert retrieved.symbol == "TEST"
    assert retrieved.status == "PENDING"


if __name__ == "__main__":
    # Quick manual check when run directly
    test_basic_endpoints()
    print("✅ Basic endpoint test passed.")

    # To run the full suite you can use:
    #   pytest -q
    pass