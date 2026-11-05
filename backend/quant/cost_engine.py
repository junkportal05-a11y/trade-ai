"""
backend/quant/cost_engine.py — NSE Transaction Cost & Slippage Model
====================================================================
Real-world backtests must pay for trading. The model is a conservative
per-side composition of:

- Slippage ........... 5.0 bps per side  (fixed, mandated: ~0.05%)
- Brokerage .......... 1.0 bps per side  (discount broker, ~Rs.20 per ~Rs.2L leg)
- Exchange turnover .. 0.297 bps per side (NSE cash-segment transaction charge)
- SEBI fee ........... 0.001 bps per side
- Stamp duty ......... 0.3 bps on buy leg only (0.15 bps averaged over sides)
- GST ................ 18% on (brokerage + exchange + SEBI) ~= 0.234 bps
- STT ................ sell-leg only; intraday 2.5 bps (1.25 avg/side),
                          delivery 10.0 bps (5.0 avg/side)

resulting TOTAL_PER_SIDE:
  intraday ~= 7.9 bps      -> round trip ~15.8 bps
  delivery ~= 11.7 bps     -> round trip ~23.4 bps (conservative default used by
                             the daily-bar tournament and backtest engines)
"""
from __future__ import annotations

BPS: float = 10_000.0

# Component breakdown (basis points)
SLIPPAGE_BPS: float = 5.0
BROKERAGE_BPS: float = 1.0
EXCHANGE_TURNOVER_BPS: float = 0.297
SEBI_FEE_BPS: float = 0.001
STAMP_DUTY_BPS_BUY_ONLY: float = 0.3          # averaged over both sides -> 0.15
GST_RATE: float = 0.18                        # on brokerage + exchange + SEBI


def _gst_bps() -> float:
    return GST_RATE * (BROKERAGE_BPS + EXCHANGE_TURNOVER_BPS + SEBI_FEE_BPS)


def _stt_avg_bps(product: str) -> float:
    """STT averaged over buy+sell legs (charge applies to the sell leg only)."""
    stt_sell_leg = 2.5 if product == "intraday" else 10.0  # NSE cash segment
    return stt_sell_leg / 2.0


def composed_side_cost_bps(product: str = "delivery") -> float:
    """Total per-side cost in bps for the given product ('intraday'|'delivery')."""
    stamps = STAMP_DUTY_BPS_BUY_ONLY / 2.0  # applies to buys; averaged per side
    return round(
        SLIPPAGE_BPS
        + BROKERAGE_BPS
        + EXCHANGE_TURNOVER_BPS
        + SEBI_FEE_BPS
        + stamps
        + _gst_bps()
        + _stt_avg_bps(product),
        3,
    )


# Temporal default: multi-day daily-bar simulations default to delivery costs.
DEFAULT_SIDE_COST_BPS: float = composed_side_cost_bps("delivery")


class CostEngine:
    """Per-side NSE cost model used across simulation engines."""

    BPS: float = BPS  # 10_000.0 basis points per unit return
    DEFAULT_SIDE_COST_BPS: float = DEFAULT_SIDE_COST_BPS

    def __init__(self, side_cost_bps: float = None, product: str = "delivery"):
        if product not in ("intraday", "delivery"):
            raise ValueError("product must be 'intraday' or 'delivery'")
        self.side_cost_bps = float(
            side_cost_bps if side_cost_bps is not None else composed_side_cost_bps(product)
        )
        if self.side_cost_bps < 0:
            raise ValueError("side_cost_bps must be non-negative")

    @property
    def side_cost_rate(self) -> float:
        """Cost as a fraction of traded notional for one side (execution)."""
        return self.side_cost_bps / BPS

    @staticmethod
    def sides_for_turn(prev_position: float, new_position: float) -> int:
        """
        Number of executions implied by moving from `prev_position` to
        `new_position` (position units are fraction-of-notional, signed).

        0 -> hold (no change)
        1 -> open a new position OR close to flat
        2 -> flip long<->short (close one side, open the other)
        """
        if prev_position == new_position:
            return 0
        if prev_position == 0 or new_position == 0:
            return 1
        if prev_position * new_position < 0:
            return 2
        return 1

    def turnover_cost(self, prev_position: float, new_position: float) -> float:
        """Fraction of turnover notional burned as cost in a single rebalance."""
        return self.side_cost_rate * self.sides_for_turn(prev_position, new_position)

    def calculate(self, notional: float = 1.0, prev_position: float = 0.0, new_position: float = 0.0) -> float:
        """Cost in notional units for rebalancing from prev -> new position."""
        return self.turnover_cost(prev_position, new_position) * (notional if notional else 1.0)
