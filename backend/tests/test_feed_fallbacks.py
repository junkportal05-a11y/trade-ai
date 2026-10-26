"""Feed fallback and caching tests (TAR-16).

Covers the quote fallback chain (cache → AngelOne → yfinance → stale cache),
last-known-good candle snapshots, and the AngelOne auto-login stampede guard.
All network and SDK calls are mocked — nothing touches AngelOne or Yahoo.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

import signals


@pytest.fixture(autouse=True)
def _reset_feed_caches():
    for cache in (
        signals.QUOTE_CACHE,
        signals.QUOTE_CACHE_TS,
        signals._YF_FAIL_TS,
        signals._BATCH_CANDLE_CACHE,
        signals._CACHE_TIMESTAMP,
    ):
        cache.clear()
    yield
    for cache in (
        signals.QUOTE_CACHE,
        signals.QUOTE_CACHE_TS,
        signals._YF_FAIL_TS,
        signals._BATCH_CANDLE_CACHE,
        signals._CACHE_TIMESTAMP,
    ):
        cache.clear()


def _unauthorized_feed():
    feed = MagicMock()
    feed.is_authorized.return_value = False
    return feed


def test_quote_falls_back_to_yahoo_when_unauthorized():
    ticker = MagicMock()
    ticker.fast_info.last_price = 123.45
    ticker.fast_info.previous_close = 120.00
    ticker.fast_info.last_volume = 1000
    with patch("signals.get_angelone_feed", return_value=_unauthorized_feed()), patch(
        "yfinance.Ticker", return_value=ticker
    ):
        quote = signals.get_symbol_quote("TCS")
    assert quote["price"] == 123.45
    assert quote["source"] == "yahoo"
    assert quote["change"] == 3.45
    # Result is cached as fresh
    assert signals.QUOTE_CACHE["TCS"]["price"] == 123.45


def test_quote_serves_fresh_cache_before_feed():
    signals.QUOTE_CACHE["TCS"] = {"symbol": "TCS", "price": 1.0}
    signals.QUOTE_CACHE_TS["TCS"] = time.time()
    assert signals.get_symbol_quote("TCS")["price"] == 1.0


def test_quote_serves_stale_cache_when_all_down():
    signals.QUOTE_CACHE["TCS"] = {"symbol": "TCS", "price": 2.5}
    signals.QUOTE_CACHE_TS["TCS"] = time.time() - 120  # stale but < QUOTE_STALE_MAX
    signals._YF_FAIL_TS["quote:TCS"] = time.time()  # yfinance in backoff
    with patch("signals.get_angelone_feed", return_value=_unauthorized_feed()):
        quote = signals.get_symbol_quote("TCS")
    assert quote["price"] == 2.5


def test_quote_none_when_no_providers_and_no_cache():
    signals._YF_FAIL_TS["quote:TCS"] = time.time()
    with patch("signals.get_angelone_feed", return_value=_unauthorized_feed()):
        assert signals.get_symbol_quote("TCS") is None


def test_authorized_empty_quote_is_definitive_miss():
    feed = MagicMock()
    feed.is_authorized.return_value = True
    feed.get_live_quotes.return_value = {}
    with patch("signals.get_angelone_feed", return_value=feed), patch(
        "yfinance.Ticker"
    ) as ticker:
        assert signals.get_symbol_quote("UNKNOWN") is None
        ticker.assert_not_called()


def test_yfinance_backoff_skips_provider():
    signals._YF_FAIL_TS["quote:TCS"] = time.time()
    with patch("signals.get_angelone_feed", return_value=_unauthorized_feed()), patch(
        "yfinance.Ticker"
    ) as ticker:
        assert signals.get_symbol_quote("TCS") is None
        ticker.assert_not_called()


def test_candles_serve_last_good_snapshot():
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [10]},
        index=pd.to_datetime(["2026-10-24 09:15"]),
    )
    signals._snapshot_candles("TCS_5m", df)
    signals._YF_FAIL_TS["TCS_5m"] = time.time()  # skip yfinance tier
    try:
        with patch("signals.get_angelone_feed", return_value=_unauthorized_feed()):
            out = signals.download_market_data_df("TCS", "5d", "5m")
        assert out is not None
        assert float(out["Close"].iloc[-1]) == 1.5
    finally:
        path = signals._LASTGOOD_DIR / signals._snapshot_key("TCS_5m")
        if path.exists():
            path.unlink()


def test_snapshot_respects_max_age():
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [10]},
        index=pd.to_datetime(["2026-10-24 09:15"]),
    )
    signals._snapshot_candles("OLD_5m", df)
    path = signals._LASTGOOD_DIR / signals._snapshot_key("OLD_5m")
    try:
        week_ago = time.time() - 7 * 24 * 3600
        os.utime(path, (week_ago, week_ago))
        assert signals._load_snapshot("OLD_5m", max_age_hours=24.0) is None
        assert signals._load_snapshot("OLD_5m", max_age_hours=24 * 30) is not None
    finally:
        if path.exists():
            path.unlink()


def _make_feed():
    from angelone_feed import AngelOneFeed

    with patch("angelone_feed.SmartConnect"), patch("angelone_feed.db") as mock_db:
        mock_db.get_angelone_session.return_value = {}
        feed = AngelOneFeed()
    return feed


def test_auto_login_cooldown_skips_retry():
    feed = _make_feed()
    feed._last_login_attempt = time.time()
    feed.session_token = None
    assert feed.auto_login() is False  # cooldown path: no db/SDK calls


def test_auto_login_cooldown_reports_live_session():
    feed = _make_feed()
    feed._last_login_attempt = time.time()
    feed.session_token = "tok"
    assert feed.auto_login() is True


def test_auto_login_waits_for_inflight_login():
    feed = _make_feed()
    feed._login_lock.acquire()
    feed.session_token = "tok"
    try:
        ex = ThreadPoolExecutor(1)
        fut = ex.submit(feed.auto_login)
        time.sleep(0.2)
        feed._login_lock.release()
        assert fut.result(timeout=10) is True
    finally:
        ex.shutdown(wait=True)
