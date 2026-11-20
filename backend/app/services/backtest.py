"""Backtest service wrapper."""
from __future__ import annotations

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backtest_engine import BacktestConfig, run_historical_backtest


def run_backtest(symbol: str = "RELIANCE.NS", config: BacktestConfig | None = None) -> dict:
    """Run the single daily-trend backtest through the shared engine."""
    return run_historical_backtest(symbol, config or BacktestConfig())
