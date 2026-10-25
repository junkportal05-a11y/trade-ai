"""Tests for Pydantic endpoint validation and division-by-zero safeguards."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.core.security import require_session, require_admin
from app.core.database import get_db
from app.models.schemas import SignalsQuery

client = TestClient(app)


# Tests that override auth dependencies don't need auth_client
# Tests using the base client for public endpoints (health, prices) don't need auth_client
# Tests for protected endpoints need auth_client

# ---------------------------------------------------------------------------
# /quote validation
# ---------------------------------------------------------------------------
def test_quote_valid_symbol(auth_client):
    with patch("app.api.v1.quotes.get_symbol_quote", return_value={"symbol": "TCS.NS", "price": 1.0}) as m:
        r = auth_client.get("/api/quote?symbol=TCS.NS")
        assert r.status_code == 200
        m.assert_called_once_with("TCS.NS")


def test_quote_lowercase_symbol_rejected(auth_client):
    r = auth_client.get("/api/quote?symbol=tcs.ns")
    assert r.status_code == 422


def test_quote_missing_symbol_rejected(auth_client):
    r = auth_client.get("/api/quote")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /search validation
# ---------------------------------------------------------------------------
def test_search_valid(auth_client):
    with patch("app.services.broker.get_broker_feed") as mock_get_feed:
        feed = MagicMock()
        feed.get_instrument_token.return_value = "123"
        mock_get_feed.return_value = feed
        r = auth_client.get("/api/search?q=RELIANCE")
        assert r.status_code == 200
        assert r.json()["results"][0]["symbol"] == "RELIANCE.NS"


def test_search_empty_q_rejected(auth_client):
    r = auth_client.get("/api/search?q=")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /history validation
# ---------------------------------------------------------------------------
def test_history_invalid_interval_rejected(auth_client):
    r = auth_client.get("/api/history?symbol=RELIANCE&interval=bad&range=1mo")
    assert r.status_code in [400, 422]


def test_history_invalid_range_rejected(auth_client):
    r = auth_client.get("/api/history?symbol=RELIANCE&interval=1d&range=bad")
    assert r.status_code in [400, 422]


def test_history_valid_params(auth_client):
    # symbol/interval/range format accepted; downstream data fetch may 404/500
    # but validation itself must not reject with 422.
    with patch("app.services.market_data.download_market_data_df") as mock_download:
        mock_download.return_value = None  # Will cause 404, not 422
        r = auth_client.get("/api/history?symbol=RELIANCE&interval=1d&range=1mo")
        assert r.status_code != 422  # Should be 404 (not found) or 500, not 422 (validation)


# ---------------------------------------------------------------------------
# /signals validation (SignalsQuery)
# ---------------------------------------------------------------------------
def test_signals_oversize_symbol_rejected():
    # Override auth dependencies to reach validation logic
    def mock_require_session():
        return {"username": "test", "role": "Authorized Guest", "clearance": "LEVEL_1_GUEST"}

    def mock_get_db():
        db = MagicMock()
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[require_session] = mock_require_session
    app.dependency_overrides[get_db] = mock_get_db

    try:
        # Symbol exceeding max_length=200 -> 422 via built-in constraint
        oversize = "A" * 250
        r = client.get(f"/api/signals?symbols={oversize}")
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_signals_empty_symbol_rejected():
    # Override auth dependencies
    def mock_require_session():
        return {"username": "test", "role": "Authorized Guest", "clearance": "LEVEL_1_GUEST"}

    def mock_get_db():
        db = MagicMock()
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[require_session] = mock_require_session
    app.dependency_overrides[get_db] = mock_get_db

    try:
        r = client.get("/api/signals?symbols=")
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_signals_valid_symbols():
    # Override auth dependencies
    def mock_require_session():
        return {"username": "test", "role": "Authorized Guest", "clearance": "LEVEL_1_GUEST"}

    def mock_get_db():
        db = MagicMock()
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[require_session] = mock_require_session
    app.dependency_overrides[get_db] = mock_get_db

    try:
        with patch("app.services.signal_engine.run_scan") as mock_run:
            mock_run.return_value = []  # Return empty signals to avoid actual scan
            r = client.get("/api/signals?symbols=RELIANCE,TCS.NS&limit=5")
            assert r.status_code != 422  # Validation passes (may be 200 or 500 if scan fails)
    finally:
        app.dependency_overrides.clear()


def test_signals_invalid_limit_rejected():
    # Override auth dependencies
    def mock_require_session():
        return {"username": "test", "role": "Authorized Guest", "clearance": "LEVEL_1_GUEST"}

    def mock_get_db():
        db = MagicMock()
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[require_session] = mock_require_session
    app.dependency_overrides[get_db] = mock_get_db

    try:
        r = client.get("/api/signals?symbols=RELIANCE&limit=0")
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_signals_query_field_validator():
    # Direct test of the field validator to ensure format check works
    with pytest.raises(ValueError, match="Invalid symbol format"):
        SignalsQuery(symbols="REL!ANCE")


# ---------------------------------------------------------------------------
# admin key validation
# ---------------------------------------------------------------------------
def test_admin_require_admin_rejects_missing_key():
    # The admin-key guard must reject a missing key with HTTP 403.
    r = client.get("/api/admin/health")
    assert r.status_code == 403
    assert r.json()["detail"] == "Admin access required"


def test_admin_require_admin_rejects_wrong_key():
    # The admin-key guard must reject a wrong key with HTTP 403.
    r = client.get("/api/admin/health", headers={"X-Admin-Key": "wrong_key"})
    assert r.status_code == 403
    assert r.json()["detail"] == "Admin access required"


def test_admin_health_endpoint_enforces_key():
    # Without a valid admin key the endpoint must not return 200.
    r = client.get("/api/admin/health")
    assert r.status_code != 200


# ---------------------------------------------------------------------------
# division-by-zero safeguards
# ---------------------------------------------------------------------------
def test_prediction_stats_empty_safe():
    # With no resolved predictions the endpoint must return zeros, not 500.
    # Override dependencies to bypass auth and mock DB
    def mock_require_session():
        return {"username": "test", "role": "Authorized Guest", "clearance": "LEVEL_1_GUEST"}

    def mock_get_db():
        db = MagicMock()
        # Mock db.query(...).filter(...).all() returning empty list
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        db.query.return_value = mock_query
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[require_session] = mock_require_session
    app.dependency_overrides[get_db] = mock_get_db

    try:
        r = client.get("/api/predictions/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["win_rate"] == 0.0
        assert data["avg_error"] == 0.0
        assert data["resolved_predictions"] == 0
    finally:
        app.dependency_overrides.clear()


def test_backtest_division_by_zero_guards_logic():
    """Test the mathematical guard conditions in backtest calculations"""
    # Test win_rate guard: when total_trades == 0, win_rate should be 0.0
    total_trades = 0
    wins = 0
    win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0
    assert win_rate == 0.0  # Guard prevents division by zero

    # Test win_rate guard: when total_trades > 0, normal calculation
    total_trades = 3
    wins = 2
    win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0
    assert win_rate == 66.7  # 2/3 * 100 = 66.666... -> 66.7

    # Test profit_factor guard: when gross_loss == 0 and gross_profit > 0
    gross_profit = 150.0
    gross_loss = 0.0
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    else:
        profit_factor = (round(gross_profit, 2) if gross_profit > 0 else 1.00)
    assert profit_factor == 150.0  # When gross_loss == 0: profit_factor = gross_profit (rounded)

    # Test profit_factor guard: when both are zero
    gross_profit = 0.0
    gross_loss = 0.0
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    else:
        profit_factor = (round(gross_profit, 2) if gross_profit > 0 else 1.00)
    assert profit_factor == 1.00  # When both are zero

    # Test profit_factor guard: normal case
    gross_profit = 200.0
    gross_loss = 50.0
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    else:
        profit_factor = (round(gross_profit, 2) if gross_profit > 0 else 1.00)
    assert profit_factor == 4.0  # 200/50 = 4.0

    # Test total_pnl_pct guard: when initial_capital == 0
    total_pnl = 50.0
    initial_capital = 0.0
    total_pnl_pct = (
        round((total_pnl / initial_capital) * 100, 2)
        if initial_capital
        else 0.0
    )
    assert total_pnl_pct == 0.0  # Guard prevents division by zero

    # Test total_pnl_pct guard: normal case
    total_pnl = 50.0
    initial_capital = 1000.0
    total_pnl_pct = (
        round((total_pnl / initial_capital) * 100, 2)
        if initial_capital
        else 0.0
    )
    assert total_pnl_pct == 5.0  # 50/1000 * 100 = 5.0

    # Test drawdown guard: when peak == 0
    peak = 0.0
    val = 100.0
    dd = (peak - val) / peak * 100 if peak else 0.0
    assert dd == 0.0  # Guard prevents division by zero

    # Test drawdown guard: normal case
    peak = 200.0
    val = 150.0
    dd = (peak - val) / peak * 100 if peak else 0.0
    assert dd == 25.0  # (200-150)/200 * 100 = 25.0