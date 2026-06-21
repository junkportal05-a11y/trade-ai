import pytest
from backtest_engine import resolve_candle_pessimistic

def test_both_tp_and_sl_touched_same_candle_returns_loss():
    """The critical case — this is the whole point of Phase 0."""
    candle = {"high": 110, "low": 90, "open": 100}  # both target(108) and stop(92) touched
    result, price = resolve_candle_pessimistic(
        candle, entry=100, target=108, stop=92, direction="BUY"
    )
    assert result == "LOSS"
    assert price == 92

def test_only_target_touched_returns_win():
    candle = {"high": 110, "low": 99, "open": 100}
    result, price = resolve_candle_pessimistic(
        candle, entry=100, target=108, stop=92, direction="BUY"
    )
    assert result == "WIN"
    assert price >= 108

def test_neither_touched_returns_none():
    candle = {"high": 103, "low": 99, "open": 100}
    result, price = resolve_candle_pessimistic(
        candle, entry=100, target=108, stop=92, direction="BUY"
    )
    assert result is None
