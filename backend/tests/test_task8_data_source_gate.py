"""TAR-20 Task 8: data_source honesty gate.

- Signals whose candles came from a synthetic fallback (or carry no/unknown
  data_source) must NEVER become paper trades.
- Real-tier signals (angelone/yfinance/last-good) trade, and their payloads
  carry the tier tag through prediction + journal.
- run_scan rows carry data_source from the download tier cache.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest


# ── Paper loop harness: one iteration of trading_agent_loop ──────────────────
async def _run_agent_one_iteration(
    scan_result: list,
    open_positions: list | None = None,
    bot_state: str = "RUNNING",
):
    """Run trading_agent_loop exactly once. Returns (add_prediction_mock, journal_mock)."""
    from app.core.worker_state import clear_all_degraded_workers
    clear_all_degraded_workers()

    sleep_calls = 0

    async def sleep_side_effect(*args, **kwargs):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise asyncio.CancelledError("Stop after one iteration")
        await asyncio.sleep(0)

    mock_now_utc = datetime(2026, 10, 20, 4, 30, tzinfo=timezone.utc)  # Tuesday 10:00 IST

    with patch("trading_agent.db.get_bot_state", return_value=bot_state), \
         patch("trading_agent.signals.run_scan", return_value=scan_result), \
         patch("trading_agent.TradeQualityEngine.calculate_tqs", return_value={"classification": "INTRADAY_CANDIDATE"}), \
         patch("trading_agent.CorrelationEngine") as mock_corr_engine_class, \
         patch("trading_agent.db.add_prediction") as mock_add_prediction, \
         patch("trading_agent.db.add_journal_entry") as mock_journal, \
         patch("trading_agent.db.get_predictions", return_value=open_positions or []), \
         patch("trading_agent.schedule.run_pending"), \
         patch("asyncio.sleep", side_effect=sleep_side_effect), \
         patch("trading_agent.datetime") as mock_datetime:

        mock_datetime.now.return_value = mock_now_utc
        mock_datetime.timezone = timezone
        mock_datetime.timedelta = timedelta

        corr = MagicMock()
        corr.check_trade_allowed.return_value = True
        corr.last_built_date = None
        mock_corr_engine_class.return_value = corr

        import trading_agent

        try:
            await trading_agent.trading_agent_loop()
        except asyncio.CancelledError:
            pass

        return mock_add_prediction, mock_journal


def _signal(symbol: str = "RELIANCE.NS", data_source=None) -> dict:
    sig = {
        "symbol": symbol,
        "signal": "BUY",
        "price": 100.0,
        "confidence": 80,
        "target": 110.0,
        "stop_loss": 95.0,
        "atr": 2.0,
        "vol_ratio": 1.5,
        "market_regime_snapshot": "BULLISH",
        "setup_type": "TEST",
        "sector": "FINANCIAL",
        "nifty_trend": "BULLISH",
        "reasoning": "unit fixture",
        "signal_time": datetime.now(timezone.utc).isoformat(),
        "order_time": datetime.now(timezone.utc).isoformat(),
    }
    if data_source is not None:
        sig["data_source"] = data_source
    return sig


@pytest.mark.asyncio
async def test_synthetic_signal_never_trades():
    mock_add, mock_journal = await _run_agent_one_iteration([_signal(data_source="synthetic")])
    assert mock_add.call_count == 0  # synthetic fallback must not become a paper trade
    assert mock_journal.call_count == 0


@pytest.mark.asyncio
async def test_untagged_signal_fails_closed():
    mock_add, mock_journal = await _run_agent_one_iteration([_signal(data_source=None)])
    assert mock_add.call_count == 0  # no data_source -> treated as simulated
    assert mock_journal.call_count == 0


@pytest.mark.asyncio
async def test_real_tier_signals_trade_and_carry_data_source():
    for tier in ("angelone", "yfinance", "last-good"):
        mock_add, mock_journal = await _run_agent_one_iteration([_signal(data_source=tier)])
        assert mock_add.call_count == 1, f"tier={tier} should trade"
        payload = mock_add.call_args[0][0]
        assert payload["data_source"] == tier
        assert payload["order_mode"] == "paper"
        journal_entry = mock_journal.call_args[0][0]
        assert journal_entry["data_source"] == tier


@pytest.mark.asyncio
async def test_seed_and_unknown_source_never_trade():
    for bad_source in ("seed", "simulated", "quantum-broker"):
        mock_add, _ = await _run_agent_one_iteration([_signal(data_source=bad_source)])
        assert mock_add.call_count == 0, f"unknown tier {bad_source} must not trade"


def test_payload_builders_pass_data_source_through():
    from trading_agent import _build_prediction_payload, _build_journal_payload

    sig = _signal(data_source="yfinance")
    pred = _build_prediction_payload(sig)
    journal = _build_journal_payload(sig)
    assert pred["data_source"] == "yfinance"
    assert journal["data_source"] == "yfinance"
    sig2 = _signal()  # untagged
    assert _build_prediction_payload(sig2)["data_source"] is None
    assert _build_journal_payload(sig2)["data_source"] is None


# ── run_scan integration harness ─────────────────────────────────────────────
def _scan_fixture_matrix() -> pd.DataFrame:
    """60+bar daily matrix that clears the real gates (volume surge, trend,
    validation): oscillating uptrend breaks above the running VWAP, volume
    ramps into a final surge bar."""
    n = 120
    idx = np.arange(n)
    prices = np.array([200.0 + 0.15 * j + 2.5 * np.sin(j / 2.5) for j in idx])
    prices[100:] = prices[100:] + 8.0  # lift price above the running VWAP
    volume = np.array([1000.0] * 79 + [2500.0] * 20 + [4000.0] * 20 + [6000.0])
    return pd.DataFrame(
        {
            "Open": prices - 0.2,
            "High": prices + 0.8,
            "Low": prices - 0.8,
            "Close": prices,
            "Volume": volume,
        },
        index=pd.date_range("2023-01-02", periods=n, freq="1D"),
    )


def _patch_scan_environment(monkeypatch, download_frame: pd.DataFrame, seed_cache: bool):
    """Point the scan pipeline at the offline matrix and (optionally) record a
    feed tier in _SOURCE_CACHE, as the tiered download chain would."""
    import signals
    import app.services.signal_engine as engine

    monkeypatch.setattr(signals, "is_nse_market_open", lambda: False)
    monkeypatch.setattr(signals, "download_market_data_df", lambda *a, **kw: download_frame.copy())
    # Pure veto gates are seam-patched; the volume/trend/confidence gates run real.
    monkeypatch.setattr(signals, "vwap_veto", lambda price, vwap, sig: (True, None))
    monkeypatch.setattr(signals, "validate_risk_reward", lambda *a, **kw: True)
    monkeypatch.setattr(engine, "NSE_WATCHLIST", [{"symbol": "TEST.NS", "name": "Test", "sector": "Energy"}])
    if seed_cache:
        signals._SOURCE_CACHE["TEST.NS_1d"] = "yfinance"


def test_run_scan_rows_carry_data_source_tier(monkeypatch):
    """run_scan rows expose the feed tier that served the scan frame."""
    import signals

    _patch_scan_environment(monkeypatch, _scan_fixture_matrix(), seed_cache=True)
    signals._MACRO_CACHE.pop("TEST.NS", None)
    cache_key = "TEST.NS_1d"
    try:
        rows = signals.run_scan(
            [{"symbol": "TEST.NS", "name": "Test", "sector": "Energy"}],
            "1d", "Intraday Momentum", "Medium", "NSE", 100000.0,
        )
    finally:
        signals._SOURCE_CACHE.pop(cache_key, None)
        signals._MACRO_CACHE.pop("TEST.NS", None)

    assert isinstance(rows, list) and rows, "scan should produce at least one row"
    assert all(r.get("data_source") == "yfinance" for r in rows), \
        "every scanned row must carry the feed tier of its scan frame"


def test_run_scan_rows_data_source_null_when_unknown(monkeypatch):
    """Honesty: rows carry None (not a guessed tier) when the chain bypassed the cache."""
    import signals

    _patch_scan_environment(monkeypatch, _scan_fixture_matrix(), seed_cache=False)
    signals._MACRO_CACHE.pop("TEST.NS", None)

    rows = signals.run_scan(
        [{"symbol": "TEST.NS", "name": "Test", "sector": "Energy"}],
        "1d", "Intraday Momentum", "Medium", "NSE", 100000.0,
    )
    assert isinstance(rows, list) and rows
    assert all(r.get("data_source") is None for r in rows)
