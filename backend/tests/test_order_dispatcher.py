"""Unit tests for place_order dispatcher in angelone_feed.py.

SmartConnect 100% mocked — no real network calls to AngelOne.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import require_session
from backend.app.main import app
from backend.angelone_feed import AngelOneFeed

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _authed_headers(role="Trader", clearance="LEVEL_2_TRADER"):
    app.dependency_overrides[require_session] = lambda: {
        "username": "trader_user",
        "role": role,
        "clearance": clearance,
    }


def _mock_smart_api():
    """100% mocked SmartConnect — never touches network."""
    sdk = MagicMock()
    sdk.placeOrderFullResponse.return_value = {
        "status": True,
        "message": "SUCCESS",
        "data": {"orderid": "LIVE-ORDER-12345"},
    }
    return sdk


def _paper_params(symbol="RELIANCE.NS", prediction_id=1,
                  entry_price=100.0, stop_loss=90.0):
    return {
        "symbol": symbol,
        "prediction_id": prediction_id,
        "action": "BUY",
        "quantity": 100,
        "order_type": "MARKET",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
    }


# --------------------------------------------------------------------------- #
# Dynamic slippage model
# --------------------------------------------------------------------------- #

class TestSlippageModel:
    def test_slippage_scales_with_stop_distance(self):
        """Wider stop → more slippage allowed (proportional)."""
        feed = AngelOneFeed()
        # 10% stop distance (100/110/90 setup) → 10 * 0.15 = 1.5% → capped at 1.0%
        slippage = feed._compute_slippage_pct("RELIANCE.NS", 100.0, 90.0)
        assert slippage == 1.0  # capped

    def test_slippage_tight_stop_lower(self):
        """Tighter stop → less slippage."""
        feed = AngelOneFeed()
        # 1% stop distance → 0.15% → above 0.05% min
        slippage = feed._compute_slippage_pct("RELIANCE.NS", 100.0, 99.0)
        assert abs(slippage - 0.15) < 0.01

    def test_slippage_floor(self):
        """Zero entry or stop → minimum floor 0.05%."""
        feed = AngelOneFeed()
        slippage = feed._compute_slippage_pct("RELIANCE.NS", 0.0, 0.0)
        assert slippage == 0.05

    def test_slippage_returns_percent(self):
        """Slippage is expressed as percentage (not fraction)."""
        feed = AngelOneFeed()
        slippage = feed._compute_slippage_pct("TCS.NS", 200.0, 180.0)
        assert 0 < slippage <= 1.0


# --------------------------------------------------------------------------- #
# Paper-mode tests (TRADING_MODE=paper / LIVE_TRADING_ARMED=False — default)
# --------------------------------------------------------------------------- #

class TestPaperMode:
    def test_paper_returns_place_order_full_response_shape(self):
        """Paper path must return shape identical to AngelOne placeOrderFullResponse."""
        feed = AngelOneFeed()
        result = feed.place_order(_paper_params())
        assert result["status"] is True
        assert result["message"] == "SUCCESS"
        assert "orderid" in result.get("data", {})

    def test_paper_returns_slippage_pct(self):
        """Paper fill includes computed slippage_pct."""
        feed = AngelOneFeed()
        result = feed.place_order(_paper_params())
        assert "slippage_pct" in result["data"]
        assert isinstance(result["data"]["slippage_pct"], float)

    def test_paper_orderid_tagged_paper(self):
        """Paper fill orderid carries -PAPER- tag so callers can distinguish."""
        feed = AngelOneFeed()
        result = feed.place_order(_paper_params(prediction_id=42))
        orderid = result["data"]["orderid"]
        assert "PAPER" in orderid
        assert "42" in orderid  # idempotency key encoded in orderid

    def test_paper_no_broker_call(self):
        """Paper path must never invoke SmartConnect placeOrderFullResponse."""
        feed = AngelOneFeed()
        with patch.object(feed, "smart_api", create=True, new_callable=MagicMock) as mock_sdk:
            feed.place_order(_paper_params())
        mock_sdk.placeOrderFullResponse.assert_not_called()


# --------------------------------------------------------------------------- #
# Idempotency
# --------------------------------------------------------------------------- #

class TestIdempotency:
    def test_same_prediction_id_deduplicates(self):
        """Submitting identical prediction_id twice returns same orderid."""
        feed = AngelOneFeed()
        params = _paper_params(prediction_id=99)
        first = feed.place_order(params)
        second = feed.place_order(params)
        assert first["data"]["orderid"] == second["data"]["orderid"]

    def test_different_prediction_id_different_order(self):
        """Different prediction_id must produce different orderid."""
        feed = AngelOneFeed()
        a = feed.place_order(_paper_params(prediction_id=1))
        b = feed.place_order(_paper_params(prediction_id=2))
        assert a["data"]["orderid"] != b["data"]["orderid"]


# --------------------------------------------------------------------------- #
# Live-mode gate (both gates must pass — config + armed)
# --------------------------------------------------------------------------- #

class TestLiveGate:
    @patch("app.core.config.settings")
    def test_live_mode_not_armed_falls_to_paper(self, mock_settings):
        """TRADING_MODE=live but LIVE_TRADING_ARMED=False → paper fill (not live)."""
        mock_settings.trading_mode = "live"
        mock_settings.live_trading_armed = False
        feed = AngelOneFeed()
        result = feed.place_order(_paper_params())
        assert result["status"] is True
        assert "PAPER" in result["data"]["orderid"]

    @patch("app.core.config.settings")
    def test_paper_mode_falls_to_paper(self, mock_settings):
        """TRADING_MODE=paper → paper fill regardless of armed flag."""
        mock_settings.trading_mode = "paper"
        mock_settings.live_trading_armed = True
        feed = AngelOneFeed()
        result = feed.place_order(_paper_params())
        assert result["status"] is True
        assert "PAPER" in result["data"]["orderid"]
