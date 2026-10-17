"""Risk engine for order safety validation and position sizing."""
from __future__ import annotations

from typing import Dict


def calculate_order_safety(
    capital: float,
    entry_price: float,
    stop_loss: float,
    risk_pct: float,
    max_drawdown_pct: float,
    open_positions_risk: float,
) -> Dict[str, float | str]:
    """Calculate order safety, position size, and risk metrics.

    Validates all inputs, computes recommended position size, max dollar loss,
    and risk-to-reward ratio. Applies a circuit-breaker against max drawdown.

    Returns a dict with keys: quantity, max_dollar_loss, risk_to_reward,
    circuit_breaker_reason (empty string if passed).
    """
    EPS = 1e-12

    # ── Input validation ──────────────────────────────────────────
    if capital <= 0:
        raise ValueError("capital must be positive")
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if stop_loss <= 0:
        raise ValueError("stop_loss must be positive")
    if not (0 < risk_pct <= 100):
        raise ValueError("risk_pct must be in (0, 100]")
    if not (0 <= max_drawdown_pct <= 100):
        raise ValueError("max_drawdown_pct must be in [0, 100]")
    if not (0 <= open_positions_risk <= 100):
        raise ValueError("open_positions_risk must be in [0, 100]")

    # stop-loss nonsensical if at or beyond entry for a long trade
    if stop_loss >= entry_price:
        raise ValueError("stop_loss must be below entry_price for a long position")

    # ── Floating-point safe calculations ──────────────────────────
    risk_per_unit = abs(entry_price - stop_loss)  # dollar risk per unit/share
    if risk_per_unit < EPS:
        raise ValueError("risk_per_unit too small after validation")

    # quantity that risks exactly risk_pct% of capital
    capital_at_risk = capital * (risk_pct / 100.0)
    quantity = capital_at_risk / risk_per_unit

    max_dollar_loss = capital_at_risk

    # risk-to-reward: assume symmetrical target (1:1 R:R)
    # reward = entry_price - stop_loss (same magnitude as risk), so R:R = 1.0
    risk_to_reward = 1.0

    # ── Circuit-breaker ───────────────────────────────────────────
    new_risk_pct = risk_pct
    total_cumulative_risk_pct = open_positions_risk + new_risk_pct
    circuit_breaker_reason = ""
    if total_cumulative_risk_pct > max_drawdown_pct:
        circuit_breaker_reason = (
            f"Circuit-breaker triggered: cumulative risk {total_cumulative_risk_pct:.2f}%"
            f" exceeds max drawdown {max_drawdown_pct:.2f}%"
        )

    result: Dict[str, float | str] = {
        "quantity": round(quantity, 6),
        "max_dollar_loss": round(max_dollar_loss, 2),
        "risk_to_reward": risk_to_reward,
        "circuit_breaker_reason": circuit_breaker_reason,
    }
    return result