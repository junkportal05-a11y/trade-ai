"""Regression tests for the ApexTrade bug-repair batch (2026-10-26)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.schemas import BacktestRequest
from app.db.repositories import repo

client = TestClient(app)


def test_ws_bot_requires_token():
    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect("/ws/bot") as websocket:
            websocket.receive_text()
    except WebSocketDisconnect as exc:
        assert exc.code == 4001
    else:
        raise AssertionError("unauthenticated /ws/bot connection was accepted")


def test_legacy_and_app_db_paths_match():
    import pathlib

    import db as legacy_db
    from app.core import database

    if database.engine.url.get_backend_name() != "sqlite":
        pytest.skip("SQLite-specific path check")

    assert pathlib.Path(legacy_db.DB_PATH).resolve() == pathlib.Path(database.engine.url.database).resolve()
    assert not hasattr(repo, "broker")


def test_backtest_defaults_match_engine_scale():
    from backtest_engine import BacktestConfig

    req = BacktestRequest()
    engine = BacktestConfig()

    assert req.risk_pct == engine.risk_pct == 0.02
    assert req.entry_score == engine.entry_score == 5
    assert req.early_exit == engine.early_exit == -4
    assert req.target_atr == engine.target_atr == 2.5
    assert req.adx_min == engine.adx_min == 0.0


def test_backtest_percent_style_risk_and_zero_are_sanitized():
    assert BacktestRequest(risk_pct=2.0).risk_pct == 0.02
    assert BacktestRequest(risk_pct=0).risk_pct == 0.02
    assert BacktestRequest(risk_pct="not-a-number").risk_pct == 0.02
    assert BacktestRequest(early_exit=True).early_exit == -4


def test_services_backtest_wrapper_delegates(monkeypatch):
    from app.services import backtest as service

    captured = {}

    def fake_engine(symbol, config):
        captured["symbol"] = symbol
        captured["config"] = config
        return {"symbol": symbol}

    monkeypatch.setattr(service, "run_historical_backtest", fake_engine)
    result = service.run_backtest("TCS.NS")

    assert result == {"symbol": "TCS.NS"}
    assert captured["symbol"] == "TCS.NS"
    assert captured["config"] is not None


def test_strategies_get_and_post_require_auth():
    assert client.get("/api/strategies").status_code == 401
    assert client.post("/api/strategies", json={"name": "x"}).status_code == 401


def test_create_strategy_persists_real_id(auth_client):
    response = auth_client.post(
        "/api/strategies",
        json={"name": "Repair Test Strategy", "description": "persisted"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] != 999
    assert body["name"] == "Repair Test Strategy"

    from app.core.database import SessionLocal
    from app.db.models import Strategy

    db = SessionLocal()
    try:
        db.query(Strategy).filter(Strategy.id == body["id"]).delete()
        db.commit()
    finally:
        db.close()


def test_delete_prediction_endpoint(auth_client):
    created = auth_client.post(
        "/api/predictions",
        json={
            "symbol": "REPAIR.NS",
            "prediction_type": "BULLISH",
            "entry_price": 100.0,
            "target_price": 110.0,
            "stop_loss": 95.0,
            "confidence_score": 80,
        },
    )
    assert created.status_code == 200, created.text
    pred_id = created.json()["id"]

    deleted = auth_client.delete(f"/api/predictions/{pred_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    again = auth_client.delete(f"/api/predictions/{pred_id}")
    assert again.status_code == 404


def test_prediction_stats_expose_resolved_trade_fields(auth_client):
    response = auth_client.get("/api/predictions/stats")
    assert response.status_code == 200
    body = response.json()
    assert "avg_win" in body
    assert "avg_loss" in body
    assert body["total_trades"] == body["resolved_predictions"]


def test_data_confidence_is_unknown_without_measurement(auth_client, monkeypatch):
    monkeypatch.setattr(repo.data_quality, "get_latest", lambda _db: None)

    response = auth_client.get("/api/data/confidence?symbols=RELIANCE.NS")
    assert response.status_code == 200
    body = response.json()
    assert body["overall_confidence"] is None
    assert body["confidence_measured"] is False
    assert body["data_source"] == "NOT_MEASURED"


def test_admin_simulation_does_not_fabricate_metrics(monkeypatch):
    import backtest_engine

    monkeypatch.setattr(
        backtest_engine,
        "run_historical_backtest",
        lambda symbol, config: {"error": "no historical data"},
    )
    response = client.post(
        "/api/admin/run-simulation",
        headers={"X-Admin-Key": settings.admin_key},
        json={"symbol": "RELIANCE.NS"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["win_rate"] is None
    assert body["total_pnl_pct"] is None
    assert body["total_trades"] is None


def test_worker_status_uses_feed_auth_state(monkeypatch):
    class FakeFeed:
        def is_authorized(self):
            return False

    monkeypatch.setattr("app.services.broker.get_broker_feed", lambda: FakeFeed())
    response = client.get(
        "/api/admin/worker-status",
        headers={"X-Admin-Key": settings.admin_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["angelone_authorized"] is False
    assert body["angelone_status"] == "not_authorized"


def test_bot_rejects_live_paper_flag(auth_client, monkeypatch):
    monkeypatch.setattr("db.set_bot_state", lambda state: None)

    response = auth_client.post("/api/bot/start", json={"paper": False})
    assert response.status_code == 400
    assert "paper mode only" in response.json()["detail"].lower()

    ok = auth_client.post("/api/bot/start", json={"paper": True})
    assert ok.status_code == 200
    assert ok.json()["mode"] == "paper"


def test_bot_stop_reports_square_off_exception(auth_client, monkeypatch):
    monkeypatch.setattr("db.set_bot_state", lambda state: None)

    def explode(_now):
        raise RuntimeError("boom")

    monkeypatch.setattr("trading_agent._square_off_all", explode)
    response = auth_client.post("/api/bot/stop")
    assert response.status_code == 500
    assert "boom" in response.json()["detail"]


def test_cors_rejects_unlisted_vercel_origin():
    evil = client.get("/api/", headers={"Origin": "https://evil.vercel.app"})
    assert "access-control-allow-origin" not in evil.headers

    allowed = client.get(
        "/api/",
        headers={"Origin": "https://trade-ai-beta.vercel.app"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "https://trade-ai-beta.vercel.app"
