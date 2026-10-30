"""TAR-19 P1 tests: prediction DELETE ownership scoping, strategies GET honesty,
and real avg_error (MAE) in prediction stats."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, user_registry

PRED_BODY = {
    "symbol": "tar19.NS",
    "prediction_type": "BULLISH",
    "entry_price": 100.0,
    "target_price": 110.0,
    "stop_loss": 95.0,
    "confidence_score": 80,
}


def _client_as(username: str) -> TestClient:
    user_registry._users[username] = {
        "pass_hash": "test-only",
        "role": "Trader",
        "clearance": "LEVEL_2_TRADER",
    }
    client = TestClient(app)
    client.cookies.set("apt_token", create_access_token({"sub": username}))
    client.headers["X-Requested-With"] = "XMLHttpRequest"
    return client


def test_prediction_delete_scopes_to_owner():
    owner = _client_as("tar19_owner_test")
    other = _client_as("tar19_other_trader")
    created = owner.post("/api/predictions", json=PRED_BODY)
    assert created.status_code == 200, created.text
    pred_id = created.json()["id"]

    r_other = other.delete(f"/api/predictions/{pred_id}")
    assert r_other.status_code == 404, r_other.text
    assert r_other.json()["detail"] == "Prediction not found"

    r_owner = owner.delete(f"/api/predictions/{pred_id}")
    assert r_owner.status_code == 200, r_owner.text
    assert r_owner.json()["status"] == "deleted"


def test_prediction_delete_blocks_legacy_rows():
    from app.core.database import SessionLocal
    from app.db.models import PredictionsHistory

    client = _client_as("tar19_legacy_probe")
    db = SessionLocal()
    row = PredictionsHistory(
        symbol="LEG19.NS",
        prediction_type="BULLISH",
        entry_price=10.0,
        target_price=11.0,
        stop_loss=9.0,
        confidence_score=50,
        status="PENDING",
    )
    db.add(row)
    db.commit()
    row_id = row.id
    db.close()
    try:
        r = client.delete(f"/api/predictions/{row_id}")
        assert r.status_code == 404, r.text
        assert r.json()["detail"] == "Prediction not found"
    finally:
        db = SessionLocal()
        db.query(PredictionsHistory).filter(PredictionsHistory.id == row_id).delete()
        db.commit()
        db.close()


def test_create_prediction_records_owner():
    from app.core.database import SessionLocal
    from app.db.models import PredictionsHistory

    client = _client_as("tar19_owner_probe")
    created = client.post("/api/predictions", json=PRED_BODY)
    assert created.status_code == 200, created.text
    pred_id = created.json()["id"]
    try:
        db = SessionLocal()
        row = db.query(PredictionsHistory).filter(PredictionsHistory.id == pred_id).first()
        assert row is not None
        assert row.user_id == "tar19_owner_probe", f"got {row.user_id}"
        db.close()
    finally:
        db = SessionLocal()
        db.query(PredictionsHistory).filter(PredictionsHistory.id == pred_id).delete()
        db.commit()
        db.close()


def test_strategies_get_labels_source_and_honours_active_only():
    from app.core.database import SessionLocal
    from app.db.models import Strategy

    client = _client_as("tar19_strat_probe")
    r = client.get("/api/strategies")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "success"
    assert data["data_source"] in ("db", "presets")
    if data["data_source"] == "db":
        for s in data["strategies"]:
            assert {"id", "name", "description", "is_active"} <= set(s)
            assert "win_rate" not in s

    db = SessionLocal()
    hidden = Strategy(name="Tar19Hidden", description="inactive probe", is_active=False)
    db.add(hidden)
    db.commit()
    hidden_id = hidden.id
    db.close()
    try:
        default = client.get("/api/strategies").json()
        assert all(s.get("id") != hidden_id for s in default["strategies"])

        extended = client.get("/api/strategies", params={"active_only": "false"}).json()
        assert extended["data_source"] == "db"
        assert any(s.get("id") == hidden_id for s in extended["strategies"])
    finally:
        db = SessionLocal()
        db.query(Strategy).filter(Strategy.id == hidden_id).delete()
        db.commit()
        db.close()


def test_strategies_get_falls_back_to_labelled_presets():
    from app.core.database import SessionLocal
    from app.db.models import Strategy

    db = SessionLocal()
    keep = db.query(Strategy).all()
    for row in keep:
        db.delete(row)
    db.commit()
    db.close()
    try:
        client = _client_as("tar19_preset_probe")
        data = client.get("/api/strategies").json()
        assert data["data_source"] == "presets"
        assert data["strategies"] and all("win_rate" in s for s in data["strategies"])
    finally:
        db = SessionLocal()
        for row in keep:
            db.add(row)
        db.commit()
        db.close()


def test_prediction_stats_avg_error_is_real_mae():
    from datetime import datetime, timezone

    from app.core.database import SessionLocal
    from app.db.models import PredictionsHistory

    db = SessionLocal()
    db.query(PredictionsHistory).delete()
    now = datetime.now(timezone.utc)
    db.add(
        PredictionsHistory(
            symbol="MAE1.NS",
            prediction_type="BULLISH",
            entry_price=100.0,
            target_price=110.0,
            stop_loss=90.0,
            confidence_score=70,
            status="RESOLVED",
            exit_price=105.0,
            resolved_at=now,
            pnl_pct=5.0,
        )
    )
    db.add(
        PredictionsHistory(
            symbol="MAE2.NS",
            prediction_type="BULLISH",
            entry_price=100.0,
            target_price=100.0,
            stop_loss=90.0,
            confidence_score=70,
            status="RESOLVED",
            exit_price=99.0,
            resolved_at=now,
            pnl_pct=-1.0,
        )
    )
    db.commit()
    ids = [r.id for r in db.query(PredictionsHistory).all()]
    db.close()
    try:
        client = _client_as("tar19_mae_probe")
        data = client.get("/api/predictions/stats").json()
        assert data["resolved_predictions"] == 2, data
        assert data["avg_error"] == 3.0, data["avg_error"]
    finally:
        db = SessionLocal()
        db.query(PredictionsHistory).filter(PredictionsHistory.id.in_(ids)).delete()
        db.commit()
        db.close()
