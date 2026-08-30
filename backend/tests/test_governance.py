import pytest
from unittest.mock import patch, MagicMock
from governance_worker import check_risk_limits


def test_check_risk_limits_safe():
    with patch("governance_worker.db.get_risk_settings", return_value={"daily_loss_limit": -3.0, "daily_drawdown_limit": -5.0}), \
         patch("governance_worker.db.get_portfolio_state", return_value={"current_equity": 99000.0, "daily_equity": 100000.0, "peak_equity": 100000.0}):
        result = check_risk_limits()
        assert result["triggered"] is False
        assert result["daily_loss_pct"] == -1.0
        assert result["drawdown_pct"] == -1.0


def test_check_risk_limits_daily_loss_triggered():
    with patch("governance_worker.db.get_risk_settings", return_value={"daily_loss_limit": -3.0, "daily_drawdown_limit": -5.0}), \
         patch("governance_worker.db.get_portfolio_state", return_value={"current_equity": 96000.0, "daily_equity": 100000.0, "peak_equity": 100000.0}):
        result = check_risk_limits()
        assert result["triggered"] is True
        assert "daily_loss_pct" in result["reason"]


def test_check_risk_limits_drawdown_triggered():
    with patch("governance_worker.db.get_risk_settings", return_value={"daily_loss_limit": -10.0, "daily_drawdown_limit": -4.0}), \
         patch("governance_worker.db.get_portfolio_state", return_value={"current_equity": 95000.0, "daily_equity": 95000.0, "peak_equity": 100000.0}):
        result = check_risk_limits()
        assert result["triggered"] is True
        assert "drawdown_pct" in result["reason"]