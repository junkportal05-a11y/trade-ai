"""TAR-20 Task 3: /api/market_brief — honest numbers or honest unavailability."""
import time

import pytest


@pytest.fixture(autouse=True)
def _patch_brief_engine(monkeypatch):
    """Keep /api/market_brief off the network: stub the scan engine."""
    import app.services.signal_engine as engine

    monkeypatch.setattr(engine, "NSE_WATCHLIST", ["RELIANCE.NS", "TCS.NS"])
    monkeypatch.setattr(engine, "run_scan", lambda *a, **kw: [])


def test_market_brief_requires_session():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, headers={"X-Requested-With": "XMLHttpRequest"})
    response = client.get("/api/market_brief")
    assert response.status_code == 401


def test_market_brief_ok_with_scan_data(auth_client, monkeypatch):
    import app.services.signal_engine as engine

    rows = [
        {"symbol": "RELIANCE.NS", "signal": "BUY", "confidence": 80, "price": 120.0, "ema21": 100.0},
        {"symbol": "TCS.NS", "signal": "SELL", "confidence": 55, "price": 90.0, "ema21": 100.0},
    ]
    monkeypatch.setattr(engine, "run_scan", lambda *a, **kw: rows)

    response = auth_client.get("/api/market_brief")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["nifty_trend"] == "BALANCED"  # breadth exactly 50% -> balanced
    assert data["market_sentiment_pct"] == 50  # 1 BUY of 2 scanned
    assert data["top_opportunities"][0]["symbol"] == "RELIANCE"
    assert data["top_opportunities"][0]["confidence"] == 80
    assert "1 BUY-type setup" in data["briefing_text"].replace("setups", "setup") or "1 BUY-type" in data["briefing_text"]
    assert "2 of 2" in data["briefing_text"]
    assert "had no scannable data" not in data["briefing_text"]  # nothing excluded
    assert data["risk_events"] == []


def test_market_brief_bullish_breadth_math(auth_client, monkeypatch):
    import app.services.signal_engine as engine

    rows = [
        {"symbol": "A.NS", "signal": "BUY", "confidence": 90, "price": 30.0, "ema21": 20.0},
        {"symbol": "B.NS", "signal": "BUY", "confidence": 70, "price": 30.0, "ema21": 20.0},
        {"symbol": "C.NS", "signal": "WEAK BUY", "confidence": 60, "price": 30.0, "ema21": 20.0},
    ]
    monkeypatch.setattr(engine, "run_scan", lambda *a, **kw: rows)
    monkeypatch.setattr(engine, "NSE_WATCHLIST", ["A.NS", "B.NS", "C.NS"])

    response = auth_client.get("/api/market_brief")
    data = response.json()
    assert data["nifty_trend"] == "BULLISH"  # 3/3 above EMA21
    assert data["market_sentiment_pct"] == 100
    assert "of 3 tracked" in data["briefing_text"]
    assert "had no scannable data" not in data["briefing_text"]  # nothing excluded


def test_market_brief_empty_scan_returns_honest_unavailable(auth_client):
    response = auth_client.get("/api/market_brief")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["nifty_trend"] is None
    assert data["market_sentiment_pct"] is None
    assert data["top_opportunities"] == []
    assert data["risk_events"] == []
    assert "made up" in data["briefing_text"] or "Nothing is being made up" in data["briefing_text"]


def test_market_brief_scan_crash_returns_honest_unavailable(auth_client, monkeypatch):
    import app.services.signal_engine as engine

    def _boom(*a, **kw):
        raise RuntimeError("feed exploded")

    monkeypatch.setattr(engine, "run_scan", _boom)
    response = auth_client.get("/api/market_brief")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["nifty_trend"] is None


def test_market_brief_timeout_returns_honest_unavailable(auth_client, monkeypatch):
    import app.api.v1.briefing as briefing

    monkeypatch.setattr(briefing, "BRIEF_TIMEOUT_SECONDS", 0.05)

    import app.services.signal_engine as engine

    def _slow(*a, **kw):
        time.sleep(1.5)
        return []

    monkeypatch.setattr(engine, "run_scan", _slow)
    response = auth_client.get("/api/market_brief")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert "timed out" in data["briefing_text"]
    assert data["nifty_trend"] is None
