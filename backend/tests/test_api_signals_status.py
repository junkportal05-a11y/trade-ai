"""TAR-20 Task 7: SignalResponse status/error/message/symbols_scanned — honest
values on /api/signals and /api/scan, never invented numbers."""
import time

import pytest


@pytest.fixture(autouse=True)
def _patch_scan_engine(monkeypatch):
    """Keep /api/signals off the network: stub the scan pipeline."""
    import app.services.signal_engine as engine

    monkeypatch.setattr(
        engine,
        "NSE_WATCHLIST",
        [{"symbol": "RELIANCE.NS", "name": "Reliance", "sector": "Energy"}, {"symbol": "TCS.NS", "name": "TCS", "sector": "IT"}],
    )
    monkeypatch.setattr(engine, "run_scan", lambda *a, **kw: [])


def test_signals_ok_rows_report_scanned(auth_client, monkeypatch):
    import app.services.signal_engine as engine

    rows = [
        {"symbol": "RELIANCE.NS", "signal": "BUY", "confidence": 80, "name": "Reliance", "sector": "Energy"},
        {"symbol": "TCS.NS", "signal": "SELL", "confidence": 55, "name": "TCS", "sector": "IT"},
        {"symbol": "RELIANCE.NS", "signal": "WEAK BUY", "confidence": 60, "name": "Reliance", "sector": "Energy"},
    ]
    monkeypatch.setattr(engine, "run_scan", lambda *a, **kw: rows)

    response = auth_client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["error"] is None
    assert data["symbols_scanned"] == 2  # distinct symbols, not row count
    assert data["total"] == 3
    assert len(data["signals"]) == 3
    assert data["disclaimer"]


def test_signals_all_ok_fields_present(auth_client):
    response = auth_client.get("/api/signals?symbols=RELIANCE,TCS")
    assert response.status_code == 200
    for field in ("status", "error", "message", "symbols_scanned"):
        assert field in response.json()


def test_signals_empty_scan_is_honest_unavailable(auth_client):
    response = auth_client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["error"] is None
    assert data["symbols_scanned"] == 0
    assert data["total"] == 0
    assert data["signals"] == []
    assert "made up" in data["message"].lower()


def test_signals_crash_is_honest_unavailable_with_real_error(auth_client, monkeypatch):
    import app.services.signal_engine as engine

    def _boom(*a, **kw):
        raise RuntimeError("feed exploded")

    monkeypatch.setattr(engine, "run_scan", _boom)
    response = auth_client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert "RuntimeError: feed exploded" in data["error"]
    assert data["symbols_scanned"] == 0
    assert "made up" in data["message"].lower() or "no results" in data["message"].lower()


def test_signals_timeout_is_honest_unavailable_with_real_error(auth_client, monkeypatch):
    import app.api.v1.signals as signals_api
    import app.services.signal_engine as engine

    monkeypatch.setattr(signals_api, "SIGNAL_SCAN_TIMEOUT_SECONDS", 0.05)

    def _slow(*a, **kw):
        time.sleep(1.0)
        return []

    monkeypatch.setattr(engine, "run_scan", _slow)
    response = auth_client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert "longer than 0.05s" in data["error"]
    assert "Made up" not in data["message"] and "Try again" in data["message"]
    assert data["symbols_scanned"] == 0


def test_scan_post_empty_is_honest_unavailable(auth_client):
    response = auth_client.post(
        "/api/scan",
        json={
            "symbols": ["RELIANCE.NS"],
            "interval": "15m",
            "trading_style": "Intraday Momentum",
            "risk_level": "Medium",
            "market_segment": "NSE",
            "capital": 100000.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["total"] == 0
    assert data["symbols_scanned"] == 0


def test_signal_response_schema_defaults():
    from app.models.schemas import SignalResponse

    model = SignalResponse(
        market="NSE",
        type="intraday",
        scan_time="now",
        total=0,
        signals=[],
        disclaimer="d",
    )
    assert model.status is None
    assert model.error is None
    assert model.message is None
    assert model.symbols_scanned is None
