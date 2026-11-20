"""Market data download service wrapper."""
from __future__ import annotations

import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def download_market_data_df(symbol: str, period: str = "5d", interval: str = "5m"):
    """Fetch OHLCV data — AngelOne with yfinance fallback."""
    from signals import download_market_data_df as _download
    return _download(symbol, period, interval)


def download_market_data_df_sourced(
    symbol: str, period: str = "5d", interval: str = "5m"
):
    """Same chain as download_market_data_df but returns (df, data_source).

    Calls the module-global download_market_data_df (patch seam preserved:
    tests may monkeypatch either app.services.market_data.download_market_data_df
    or signals.download_market_data_df and both are honored).
    """
    df = download_market_data_df(symbol, period, interval)  # noqa: PLC-Ripple
    if df is None:
        return None, None
    try:
        from signals import _SOURCE_CACHE

        source = _SOURCE_CACHE.get(f"{symbol}_{interval}")
    except Exception:
        source = None
    return df, source


__all__ = ["download_market_data_df", "download_market_data_df_sourced"]
