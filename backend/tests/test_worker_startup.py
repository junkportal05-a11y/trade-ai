"""Tests for fail-loud worker startup and skip_background_workers configuration."""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from app.main import app, lifespan, _attach_worker_monitor
from app.core.config import settings
from app.core.worker_state import set_degraded_worker, clear_all_degraded_workers, get_degraded_workers
from fastapi.testclient import TestClient


def test_lifespan_crashes_loudly_on_worker_startup_error():
    """Proves that when skip_background_workers is False, any worker startup failure raises immediately."""
    async def _run():
        original_skip = settings.skip_background_workers
        try:
            settings.skip_background_workers = False
            with patch("asyncio.create_task", side_effect=RuntimeError("Simulated broker/worker crash")):
                with pytest.raises(RuntimeError, match="Simulated broker/worker crash"):
                    async with lifespan(app):
                        pass
                assert app.state.worker_startup_failed == "Simulated broker/worker crash"
        finally:
            settings.skip_background_workers = original_skip

    asyncio.run(_run())


def test_lifespan_skips_workers_when_configured():
    """Proves that when skip_background_workers is True, workers are skipped cleanly without errors."""
    async def _run():
        original_skip = settings.skip_background_workers
        try:
            settings.skip_background_workers = True
            async with lifespan(app):
                assert app.state.agent_task is None
                assert app.state.resolver_task is None
                assert app.state.governance_task is None
        finally:
            settings.skip_background_workers = original_skip

    asyncio.run(_run())


def test_worker_monitor_records_crashed_worker():
    """Proves that a task raising an exception is recorded in degraded_workers."""
    async def _run():
        # Ensure clean state
        clear_all_degraded_workers()

        async def failing_task():
            await asyncio.sleep(0.01)
            raise RuntimeError("worker crashed")

        task = asyncio.create_task(failing_task())
        _attach_worker_monitor(app, task, "test_failing_worker")

        with pytest.raises(RuntimeError, match="worker crashed"):
            await task

        # Wait for callback to execute
        await asyncio.sleep(0.01)

        from app.core.worker_state import get_degraded_workers
        degraded = get_degraded_workers()
        assert "test_failing_worker" in degraded
        assert "worker crashed" in degraded["test_failing_worker"]

    asyncio.run(_run())


def test_worker_monitor_ignores_cancelled_task():
    """Proves that a cancelled task does NOT appear in degraded_workers."""
    async def _run():
        # Ensure clean state
        clear_all_degraded_workers()

        async def long_task():
            await asyncio.sleep(10)  # Never completes

        task = asyncio.create_task(long_task())
        _attach_worker_monitor(app, task, "test_cancelled_worker")

        # Cancel immediately
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Wait for callback to execute
        await asyncio.sleep(0.01)

        # Cancelled tasks must not be recorded
        from app.core.worker_state import get_degraded_workers
        degraded = get_degraded_workers()
        assert "test_cancelled_worker" not in degraded

    asyncio.run(_run())


def test_worker_status_reflects_degraded_workers():
    """Proves /api/admin/worker-status shows degraded=true and agent_running=false when degraded_workers is set."""
    # Ensure clean state
    clear_all_degraded_workers()

    # Inject a degraded worker via shared state
    from app.core.worker_state import set_degraded_worker
    set_degraded_worker("test_worker", "simulated crash")

    # Get admin key from settings
    from app.core.config import settings
    admin_key = settings.admin_key

    client = TestClient(app)
    r = client.get("/api/admin/worker-status", headers={"X-Admin-Key": admin_key})

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["degraded"] is True
    assert data["agent_running"] is False
    assert "test_worker" in data["degraded_workers"]


# ── Trading Agent Degraded Worker Tests (Real Integration Tests) ──

BUY_SIGNAL = {
    "symbol": "RELIANCE.NS",
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
    "market_cap": 1000000,
    "rsi": 60,
    "macd": 1.5,
    "adx": 25,
    "news_score": 0.5,
    "market_breadth": 0.3,
    "sector_strength": 0.4,
    "nifty_trend": "BULLISH",
    "risk_amount": 5000.0,
    "confidence_probability": 0.8,
    "regime_score": 0.7,
    "sector_score": 0.6,
    "volume_score": 0.8,
    "rs_score": 0.5,
    "trade_quality_score": 0.75,
    "correlation_score": 0.3,
    "signal_time": datetime.now(timezone.utc).isoformat(),
    "order_time": datetime.now(timezone.utc).isoformat(),
}

PENDING_POSITION = {
    "id": 1,
    "symbol": "RELIANCE.NS",
    "status": "PENDING",
    "entry_price": 100.0,
    "stop_loss": 95.0,
    "target_price": 110.0,
    "prediction_type": "BUY",
    "position_size": 1,
}


async def _run_agent_one_iteration(
    degraded_workers: dict[str, str] | None = None,
    bot_state: str = "RUNNING",
    scan_result: list | None = None,
    open_positions: list | None = None,
) -> tuple:
    """
    Run trading_agent_loop for exactly one iteration by patching asyncio.sleep
    to raise CancelledError on the second call.
    Returns (add_prediction_called, add_prediction_call_count, mock_add_prediction)
    """
    clear_all_degraded_workers()
    if degraded_workers:
        for name, reason in degraded_workers.items():
            set_degraded_worker(name, reason)

    sleep_calls = 0

    async def sleep_side_effect(*args, **kwargs):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise asyncio.CancelledError("Stop after one iteration")
        await asyncio.sleep(0)  # yield control

    # Mock datetime to simulate a weekday (Tuesday) during market hours (10:00 AM IST)
    mock_now_utc = datetime(2026, 10, 20, 4, 30, tzinfo=timezone.utc)  # Tuesday 10:00 AM IST

    with patch("trading_agent.db.get_bot_state", return_value=bot_state), \
         patch("trading_agent.signals.run_scan", return_value=scan_result or [BUY_SIGNAL]), \
         patch("trading_agent.TradeQualityEngine.calculate_tqs", return_value={"classification": "INTRADAY_CANDIDATE"}), \
         patch("trading_agent.CorrelationEngine") as mock_corr_engine_class, \
         patch("trading_agent.db.add_prediction") as mock_add_prediction, \
         patch("trading_agent.db.add_journal_entry"), \
         patch("trading_agent.db.get_predictions", return_value=open_positions or []), \
         patch("trading_agent.schedule.run_pending"), \
         patch("asyncio.sleep", side_effect=sleep_side_effect), \
         patch("trading_agent.datetime") as mock_datetime:

        mock_datetime.now.return_value = mock_now_utc
        mock_datetime.timezone = timezone
        mock_datetime.timedelta = timedelta

        mock_corr_engine = MagicMock()
        mock_corr_engine.check_trade_allowed.return_value = True
        mock_corr_engine_class.return_value = mock_corr_engine
        mock_corr_engine.last_built_date = None

        from trading_agent import trading_agent_loop

        try:
            await trading_agent_loop()
        except asyncio.CancelledError:
            pass

        return mock_add_prediction


async def _run_resolver_one_iteration(
    degraded_workers: dict[str, str] | None = None,
    pending_positions: list | None = None,
    live_quotes: dict | None = None,
) -> tuple:
    """
    Run prediction_resolver_worker for exactly one iteration.
    Returns (resolve_called, mock_resolve)
    """
    clear_all_degraded_workers()
    if degraded_workers:
        for name, reason in degraded_workers.items():
            set_degraded_worker(name, reason)

    sleep_calls = 0
    executor_calls = []

    async def sleep_side_effect(*args, **kwargs):
        nonlocal sleep_calls
        sleep_calls += 1
        # Allow multiple sleep calls (resolver sleeps in several places) before stopping
        if sleep_calls >= 5:
            raise asyncio.CancelledError("Stop after one iteration")
        await asyncio.sleep(0)

    # Mock run_in_executor to run functions synchronously (avoid thread pool issues with mocks)
    async def mock_run_in_executor(executor, func, *args, **kwargs):
        executor_calls.append(func.__name__)
        return func(*args, **kwargs)

    with patch("trading_agent.os.getenv", return_value="15"), \
         patch("app.services.market_hours.is_nse_market_open", return_value=True), \
         patch("trading_agent.db.get_predictions", return_value=pending_positions or [PENDING_POSITION]), \
         patch("angelone_feed.get_angelone_feed") as mock_feed, \
         patch("trading_agent.db.resolve_prediction") as mock_resolve, \
         patch("asyncio.sleep", side_effect=sleep_side_effect), \
         patch("asyncio.get_event_loop") as mock_get_loop:

        mock_loop = MagicMock()
        mock_loop.run_in_executor.side_effect = mock_run_in_executor
        mock_get_loop.return_value = mock_loop

        mock_feed_instance = MagicMock()
        mock_feed_instance.is_authorized.return_value = True
        mock_feed_instance.get_live_quotes.return_value = live_quotes or {"RELIANCE.NS": {"price": 112.0}}
        mock_feed.return_value = mock_feed_instance

        from trading_agent import prediction_resolver_worker

        try:
            await prediction_resolver_worker()
        except asyncio.CancelledError:
            pass

        print(f"Executor calls: {executor_calls}")
        print(f"Sleep calls: {sleep_calls}")
        return mock_resolve


def test_degraded_governance_loop_blocks_new_trade():
    """(a) governance_loop degraded -> db.add_prediction is NOT called."""
    async def _run():
        mock_add_prediction = await _run_agent_one_iteration(
            degraded_workers={"governance_loop": "crashed"},
        )
        assert mock_add_prediction.call_count == 0, "add_prediction should not be called when degraded"

    asyncio.run(_run())


def test_no_degraded_workers_allows_new_trade():
    """(b) nothing degraded -> db.add_prediction IS called once."""
    async def _run():
        mock_add_prediction = await _run_agent_one_iteration(
            degraded_workers=None,
        )
        assert mock_add_prediction.call_count == 1, "add_prediction should be called once when healthy"
        # Verify the call was made with correct symbol
        call_args = mock_add_prediction.call_args
        assert call_args is not None
        payload = call_args[0][0]  # First positional arg
        assert payload["symbol"] == "RELIANCE.NS"

    asyncio.run(_run())


def test_resolver_resolves_while_degraded():
    """(c) resolver resolves positions even when governance_loop degraded."""
    async def _run():
        mock_resolve = await _run_resolver_one_iteration(
            degraded_workers={"governance_loop": "crashed"},
            live_quotes={"RELIANCE.NS": {"price": 112.0}},  # Price crossed target (110)
        )
        assert mock_resolve.call_count == 1, "resolve_prediction should be called even when degraded"
        call_args = mock_resolve.call_args
        assert call_args is not None
        kwargs = call_args[1] if call_args[1] else {}
        assert kwargs.get("status") == "TARGET_HIT"
        assert kwargs.get("resolution_reason") == "TARGET_HIT"

    asyncio.run(_run())


def test_degraded_warning_logged_once_per_5_minutes():
    """(d) two consecutive degraded iterations -> at most one warning logged."""
    async def _run():
        clear_all_degraded_workers()
        set_degraded_worker("governance_loop", "crashed")

        sleep_calls = 0
        log_calls = []

        async def sleep_side_effect(*args, **kwargs):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 3:  # Run two iterations then stop
                raise asyncio.CancelledError("Stop after two iterations")
            await asyncio.sleep(0)

        with patch("trading_agent.db.get_bot_state", return_value="RUNNING"), \
             patch("trading_agent.signals.run_scan", return_value=[BUY_SIGNAL]), \
             patch("trading_agent.TradeQualityEngine.calculate_tqs", return_value={"classification": "INTRADAY_CANDIDATE"}), \
             patch("trading_agent.CorrelationEngine") as mock_corr_engine_class, \
             patch("trading_agent.db.add_prediction") as mock_add_prediction, \
             patch("trading_agent.db.add_journal_entry"), \
             patch("trading_agent.db.get_predictions", return_value=[]), \
             patch("trading_agent.schedule.run_pending"), \
             patch("asyncio.sleep", side_effect=sleep_side_effect), \
             patch("trading_agent.logger.warning") as mock_warning:

            mock_corr_engine = MagicMock()
            mock_corr_engine.check_trade_allowed.return_value = True
            mock_corr_engine_class.return_value = mock_corr_engine
            mock_corr_engine.last_built_date = None

            from trading_agent import trading_agent_loop

            try:
                await trading_agent_loop()
            except asyncio.CancelledError:
                pass

            # Warning should be logged exactly once (first iteration)
            # because the degraded workers set hasn't changed and <5 min elapsed
            assert mock_warning.call_count == 1, f"Expected exactly 1 warning, got {mock_warning.call_count}"
            assert "Skipping new trades - degraded workers" in mock_warning.call_args[0][0]

    asyncio.run(_run())


# ── Prediction Resolver Real Logic Tests ──

PENDING_BUY = {
    "id": 1,
    "symbol": "RELIANCE.NS",
    "status": "PENDING",
    "entry_price": 100.0,
    "stop_loss": 95.0,
    "target_price": 110.0,
    "prediction_type": "BUY",
    "position_size": 1,
    "prediction_date": datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc).isoformat(),
}

PENDING_SELL = {
    "id": 2,
    "symbol": "TCS.NS",
    "status": "PENDING",
    "entry_price": 200.0,
    "stop_loss": 210.0,
    "target_price": 180.0,
    "prediction_type": "SELL",
    "position_size": 2,
    "prediction_date": datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc).isoformat(),
}


async def _run_resolver_real(
    pending_positions: list,
    live_quotes: dict,
    degraded_workers: dict[str, str] | None = None,
) -> MagicMock:
    """
    Run the real prediction_resolver_worker for one iteration with mocked dependencies.
    Returns the mock_resolve to inspect call arguments.
    """
    clear_all_degraded_workers()
    if degraded_workers:
        for name, reason in degraded_workers.items():
            set_degraded_worker(name, reason)

    sleep_calls = 0

    async def sleep_side_effect(*args, **kwargs):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 5:
            raise asyncio.CancelledError("Stop after one iteration")
        await asyncio.sleep(0)

    async def mock_run_in_executor(executor, func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("trading_agent.os.getenv", return_value="15"), \
         patch("app.services.market_hours.is_nse_market_open", return_value=True), \
         patch("trading_agent.db.get_predictions", return_value=pending_positions), \
         patch("angelone_feed.get_angelone_feed") as mock_feed, \
         patch("trading_agent.db.resolve_prediction") as mock_resolve, \
         patch("asyncio.sleep", side_effect=sleep_side_effect), \
         patch("asyncio.get_event_loop") as mock_get_loop:

        mock_loop = MagicMock()
        mock_loop.run_in_executor.side_effect = mock_run_in_executor
        mock_get_loop.return_value = mock_loop

        mock_feed_instance = MagicMock()
        mock_feed_instance.is_authorized.return_value = True
        mock_feed_instance.get_live_quotes.return_value = live_quotes
        mock_feed.return_value = mock_feed_instance

        from trading_agent import prediction_resolver_worker

        try:
            await prediction_resolver_worker()
        except asyncio.CancelledError:
            pass

        return mock_resolve


def test_resolver_buy_hits_target():
    """BUY hits target -> resolve_prediction called with correct r_multiple and holding_time."""
    async def _run():
        mock_resolve = await _run_resolver_real(
            pending_positions=[PENDING_BUY],
            live_quotes={"RELIANCE.NS": {"price": 112.0}},  # Above target (110)
        )
        assert mock_resolve.call_count == 1
        kwargs = mock_resolve.call_args[1]
        assert kwargs["status"] == "TARGET_HIT"
        assert kwargs["resolution_reason"] == "TARGET_HIT"
        # r_multiple = (112 - 100) / |100 - 95| = 12 / 5 = 2.4
        assert kwargs["r_multiple"] == 2.4
        # holding_time_minutes should be calculated from prediction_date
        assert kwargs["holding_time_minutes"] > 0
        # pnl_inr = (112 - 100) * 1 = 12
        assert kwargs["pnl_inr"] == 12.0
        # pnl_pct = (12 / 100) * 100 = 12%
        assert kwargs["pnl_pct"] == 12.0

    asyncio.run(_run())


def test_resolver_buy_hits_stop():
    """BUY hits stop -> resolve_prediction called with correct negative r_multiple."""
    async def _run():
        mock_resolve = await _run_resolver_real(
            pending_positions=[PENDING_BUY],
            live_quotes={"RELIANCE.NS": {"price": 94.0}},  # Below stop (95)
        )
        assert mock_resolve.call_count == 1
        kwargs = mock_resolve.call_args[1]
        assert kwargs["status"] == "STOP_HIT"
        assert kwargs["resolution_reason"] == "STOP_LOSS_HIT"
        # r_multiple = (94 - 100) / |100 - 95| = -6 / 5 = -1.2
        assert kwargs["r_multiple"] == -1.2
        # pnl_inr = (94 - 100) * 1 = -6
        assert kwargs["pnl_inr"] == -6.0
        # pnl_pct = (-6 / 100) * 100 = -6%
        assert kwargs["pnl_pct"] == -6.0

    asyncio.run(_run())


def test_resolver_sell_hits_target():
    """SELL hits target -> resolve_prediction called with correct r_multiple."""
    async def _run():
        mock_resolve = await _run_resolver_real(
            pending_positions=[PENDING_SELL],
            live_quotes={"TCS.NS": {"price": 178.0}},  # Below target (180)
        )
        assert mock_resolve.call_count == 1
        kwargs = mock_resolve.call_args[1]
        assert kwargs["status"] == "TARGET_HIT"
        assert kwargs["resolution_reason"] == "TARGET_HIT"
        # r_multiple = (200 - 178) / |200 - 210| = 22 / 10 = 2.2
        assert kwargs["r_multiple"] == 2.2
        # pnl_inr = (200 - 178) * 2 = 44
        assert kwargs["pnl_inr"] == 44.0
        # pnl_pct = (22 / 200) * 100 = 11%
        assert kwargs["pnl_pct"] == 11.0

    asyncio.run(_run())


def test_resolver_sell_hits_stop():
    """SELL hits stop -> resolve_prediction called with correct negative r_multiple."""
    async def _run():
        mock_resolve = await _run_resolver_real(
            pending_positions=[PENDING_SELL],
            live_quotes={"TCS.NS": {"price": 212.0}},  # Above stop (210)
        )
        assert mock_resolve.call_count == 1
        kwargs = mock_resolve.call_args[1]
        assert kwargs["status"] == "STOP_HIT"
        assert kwargs["resolution_reason"] == "STOP_LOSS_HIT"
        # r_multiple = (200 - 212) / |200 - 210| = -12 / 10 = -1.2
        assert kwargs["r_multiple"] == -1.2
        # pnl_inr = (200 - 212) * 2 = -24
        assert kwargs["pnl_inr"] == -24.0
        # pnl_pct = (-12 / 200) * 100 = -6%
        assert kwargs["pnl_pct"] == -6.0

    asyncio.run(_run())


def test_resolver_no_live_quote_skips():
    """No live quote for symbol -> resolve_prediction NOT called."""
    async def _run():
        mock_resolve = await _run_resolver_real(
            pending_positions=[PENDING_BUY],
            live_quotes={},  # No quote for RELIANCE.NS
        )
        assert mock_resolve.call_count == 0

    asyncio.run(_run())


def test_resolver_price_between_stop_and_target_no_resolve():
    """Price between stop and target -> resolve_prediction NOT called."""
    async def _run():
        mock_resolve = await _run_resolver_real(
            pending_positions=[PENDING_BUY],
            live_quotes={"RELIANCE.NS": {"price": 102.0}},  # Between 95 and 110
        )
        assert mock_resolve.call_count == 0

    asyncio.run(_run())


def test_resolver_bad_row_followed_by_good_row():
    """Item 1: A bad row (exception during resolution) followed by a good row still resolves the good one."""
    async def _run():
        # Create a bad position (will cause an error in resolution) and a good position
        bad_position = {
            "id": 999,
            "symbol": "BAD.NS",
            "status": "PENDING",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 110.0,
            "prediction_type": "BUY",
            "position_size": 1,
            "prediction_date": datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc).isoformat(),
        }
        good_position = {
            "id": 2,
            "symbol": "GOOD.NS",
            "status": "PENDING",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 110.0,
            "prediction_type": "BUY",
            "position_size": 1,
            "prediction_date": datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc).isoformat(),
        }

        # Mock resolve_prediction to raise an exception for BAD.NS but work for GOOD.NS
        def mock_resolve_prediction(pred_id, **kwargs):
            if pred_id == 999:
                raise ValueError("Simulated DB error for BAD.NS")
            return True

        sleep_calls = 0

        async def sleep_side_effect(*args, **kwargs):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 5:
                raise asyncio.CancelledError("Stop after one iteration")
            await asyncio.sleep(0)

        async def mock_run_in_executor(executor, func, *args, **kwargs):
            return func(*args, **kwargs)

        clear_all_degraded_workers()

        with patch("trading_agent.os.getenv", return_value="15"), \
             patch("app.services.market_hours.is_nse_market_open", return_value=True), \
             patch("trading_agent.db.get_predictions", return_value=[bad_position, good_position]), \
             patch("angelone_feed.get_angelone_feed") as mock_feed, \
             patch("trading_agent.db.resolve_prediction", side_effect=mock_resolve_prediction) as mock_resolve, \
             patch("asyncio.sleep", side_effect=sleep_side_effect), \
             patch("asyncio.get_running_loop") as mock_get_loop:

            mock_loop = MagicMock()
            mock_loop.run_in_executor.side_effect = mock_run_in_executor
            mock_get_loop.return_value = mock_loop

            mock_feed_instance = MagicMock()
            mock_feed_instance.is_authorized.return_value = True
            mock_feed_instance.get_live_quotes.return_value = {
                "BAD.NS": {"price": 112.0},
                "GOOD.NS": {"price": 112.0}
            }
            mock_feed.return_value = mock_feed_instance

            from trading_agent import prediction_resolver_worker

            try:
                await prediction_resolver_worker()
            except asyncio.CancelledError:
                pass

            # The good position should still be resolved (resolve_prediction called for both, but only GOOD.NS succeeds)
            # call_count includes the failed attempt for BAD.NS
            assert mock_resolve.call_count == 2
            # Verify the successful call was for GOOD.NS (pred_id=2)
            calls = mock_resolve.call_args_list
            good_call = None
            for call in calls:
                if call[1].get('pred_id') == 2:
                    good_call = call
                    break
            assert good_call is not None, "GOOD.NS should be resolved"
            assert good_call[1]["status"] == "TARGET_HIT"

    asyncio.run(_run())


def test_resolver_zero_risk_per_share():
    """Item 2: Zero risk_per_share (entry_price == stop_loss) does not crash, r_multiple=0."""
    async def _run():
        zero_risk_position = {
            "id": 3,
            "symbol": "ZERORISK.NS",
            "status": "PENDING",
            "entry_price": 100.0,
            "stop_loss": 100.0,  # Same as entry_price -> zero risk
            "target_price": 110.0,
            "prediction_type": "BUY",
            "position_size": 1,
            "prediction_date": datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc).isoformat(),
        }

        sleep_calls = 0

        async def sleep_side_effect(*args, **kwargs):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 5:
                raise asyncio.CancelledError("Stop after one iteration")
            await asyncio.sleep(0)

        async def mock_run_in_executor(executor, func, *args, **kwargs):
            return func(*args, **kwargs)

        clear_all_degraded_workers()

        with patch("trading_agent.os.getenv", return_value="15"), \
             patch("app.services.market_hours.is_nse_market_open", return_value=True), \
             patch("trading_agent.db.get_predictions", return_value=[zero_risk_position]), \
patch("angelone_feed.get_angelone_feed") as mock_feed, \
         patch("trading_agent.db.resolve_prediction") as mock_resolve, \
         patch("asyncio.sleep", side_effect=sleep_side_effect), \
         patch("asyncio.get_running_loop") as mock_get_loop:

            mock_loop = MagicMock()
            mock_loop.run_in_executor.side_effect = mock_run_in_executor
            mock_get_loop.return_value = mock_loop

            mock_feed_instance = MagicMock()
            mock_feed_instance.is_authorized.return_value = True
            mock_feed_instance.get_live_quotes.return_value = {"ZERORISK.NS": {"price": 115.0}}  # Above target (110) to trigger TARGET_HIT
            mock_feed.return_value = mock_feed_instance

            from trading_agent import prediction_resolver_worker

            try:
                await prediction_resolver_worker()
            except asyncio.CancelledError:
                pass

            # Should not crash, should resolve with r_multiple=0
            assert mock_resolve.call_count == 1
            kwargs = mock_resolve.call_args[1]
            assert kwargs["r_multiple"] == 0.0
            assert kwargs["status"] == "TARGET_HIT"

    asyncio.run(_run())