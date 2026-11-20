"""Quote service wrapper."""
from __future__ import annotations

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from signals import get_symbol_quote

__all__ = ["get_symbol_quote"]
