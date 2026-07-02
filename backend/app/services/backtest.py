"""Backtest service wrapper."""
from __future__ import annotations

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backtest_engine import run_backtest as _run_backtest


def run_backtest() -> dict:
    return _run_backtest()
