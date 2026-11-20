"""Broker service wrapper."""
from __future__ import annotations

from functools import lru_cache



@lru_cache(maxsize=1)
def get_broker_feed():
    """Lazy singleton for broker feed."""
    # Import existing module to preserve functionality
    import sys
    import os

    # Ensure the old modules are importable from the new structure
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from angelone_feed import get_angelone_feed
    return get_angelone_feed()
