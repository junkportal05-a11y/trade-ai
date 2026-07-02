"""Market data download service wrapper."""
from __future__ import annotations

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from signals import download_market_data_df

__all__ = ["download_market_data_df"]
