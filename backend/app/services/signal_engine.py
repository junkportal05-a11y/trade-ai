"""Signal engine service wrapper."""
from __future__ import annotations

import sys
import os

# Ensure old modules are importable
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from signals import NSE_WATCHLIST, run_scan, analyse_symbol
from signals import vwap_veto, check_volume_surge, check_trend_strength

__all__ = [
    "NSE_WATCHLIST",
    "run_scan",
    "analyse_symbol",
    "vwap_veto",
    "check_volume_surge",
    "check_trend_strength",
]
