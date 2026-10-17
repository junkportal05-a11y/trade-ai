"""Pytest suite for calculate_order_safety in scripts.risk_engine."""
from __future__ import annotations

import pytest
from scripts.risk_engine import calculate_order_safety


def test_valid_order() -> None:
    """A normal long order should compute quantity and pass circuit-breaker."""
    result = calculate_order_safety(
        capital=100_000.0,
        entry_price=50.0,
        stop_loss=45.0,
        risk_pct=2.0,
        max_drawdown_pct=10.0,
        open_positions_risk=3.0,
    )
    # risk_per_unit = 5.0, capital_at_risk = 2_000, quantity = 400.0
    assert result["quantity"] == 400.0
    assert result["max_dollar_loss"] == 2000.0
    assert result["risk_to_reward"] == 1.0
    assert result["circuit_breaker_reason"] == ""


def test_inverted_stop_loss() -> None:
    """stop_loss at or above entry_price must raise ValueError."""
    with pytest.raises(ValueError, match="stop_loss must be below entry_price"):
        calculate_order_safety(
            capital=100_000.0,
            entry_price=50.0,
            stop_loss=50.0,
            risk_pct=2.0,
            max_drawdown_pct=10.0,
            open_positions_risk=3.0,
        )


def test_zero_capital() -> None:
    """capital <= 0 must raise ValueError."""
    with pytest.raises(ValueError, match="capital must be positive"):
        calculate_order_safety(
            capital=0.0,
            entry_price=50.0,
            stop_loss=45.0,
            risk_pct=2.0,
            max_drawdown_pct=10.0,
            open_positions_risk=3.0,
        )


def test_circuit_breaker_triggers() -> None:
    """Cumulative risk exceeding max drawdown must return a reason."""
    result = calculate_order_safety(
        capital=100_000.0,
        entry_price=50.0,
        stop_loss=45.0,
        risk_pct=5.0,
        max_drawdown_pct=8.0,
        open_positions_risk=5.0,
    )
    assert result["circuit_breaker_reason"] != ""
    assert "exceeds" in result["circuit_breaker_reason"]
    # quantity still computed but order effectively rejected
    assert result["quantity"] > 0


def test_risk_pct_over_limit() -> None:
    """risk_pct outside (0, 100] must raise ValueError."""
    with pytest.raises(ValueError, match="risk_pct must be in"):
        calculate_order_safety(
            capital=100_000.0,
            entry_price=50.0,
            stop_loss=45.0,
            risk_pct=110.0,
            max_drawdown_pct=10.0,
            open_positions_risk=3.0,
        )


def test_negative_open_positions_risk() -> None:
    """open_positions_risk below 0 must raise ValueError."""
    with pytest.raises(ValueError, match="open_positions_risk must be in"):
        calculate_order_safety(
            capital=100_000.0,
            entry_price=50.0,
            stop_loss=45.0,
            risk_pct=2.0,
            max_drawdown_pct=10.0,
            open_positions_risk=-1.0,
        )