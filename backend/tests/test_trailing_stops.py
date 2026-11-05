import pytest

from trading_agent import (
    TRAIL_ACTIVATION_ATR,
    TRAIL_ATR_MULT,
    _propose_trailing_stop,
    _propose_trailing_stop as _pts,
)


def _long_pred(entry=100.0, stop=97.0, atr=2.0):
    return {
        "id": 1,
        "symbol": "TEST",
        "prediction_type": "BUY",
        "entry_price": entry,
        "stop_loss": stop,
        "atr": atr,
    }


def _short_pred(entry=100.0, stop=103.0, atr=2.0):
    return {
        "id": 2,
        "symbol": "TEST",
        "prediction_type": "BEARISH",
        "entry_price": entry,
        "stop_loss": stop,
        "atr": atr,
    }


class TestLongTrail:
    def test_no_trail_before_activation(self):
        # price only 0.5 ATR above entry (activation needs 1.0 ATR)
        assert _pts(_long_pred(), 101.0) is None

    def test_trail_raises_stop_when_profitable(self):
        # price = entry + 2.0 ATR -> trail = price - 1.5 ATR = entry + 0.5 ATR
        new_stop = _pts(_long_pred(), 104.0)
        assert new_stop == round(104.0 - TRAIL_ATR_MULT * 2.0, 2)
        assert new_stop > 97.0

    def test_trail_never_loosens(self):
        # stop already trailed above the computed trail -> no update
        pred = _long_pred(entry=100.0, stop=103.5, atr=2.0)
        assert _pts(pred, 104.0) is None

    def test_trail_ratchets_up_stepwise(self):
        first = _pts(_long_pred(), 104.0)
        stepped = _long_pred(stop=first)
        second = _pts(stepped, 106.0)
        assert second is not None and second > first

    # capture TRAIL_ACTIVATION_ATR import sanity
    assert TRAIL_ACTIVATION_ATR == 1.0


class TestShortTrail:
    def test_no_trail_before_activation(self):
        assert _pts(_short_pred(), 99.0) is None

    def test_trail_lowers_stop_when_profitable(self):
        # price = entry - 2.0 ATR -> trail = price + 1.5 ATR
        new_stop = _pts(_short_pred(), 96.0)
        assert new_stop == round(96.0 + TRAIL_ATR_MULT * 2.0, 2)
        assert new_stop < 103.0

    def test_short_ratchet_only_down(self):
        pred = _short_pred(entry=100.0, stop=97.5, atr=2.0)
        assert _pts(pred, 96.0) is None


class TestGuards:
    def test_zero_atr_returns_none(self):
        assert _pts(_long_pred(atr=0.0), 104.0) is None
        assert _pts(_long_pred(atr=None), 104.0) is None

    def test_bad_price_returns_none(self):
        assert _pts(_long_pred(), 0.0) is None
        assert _pts(_long_pred(), -5.0) is None

    def test_bad_entry_returns_none(self):
        pred = _long_pred(entry=0.0)
        assert _pts(pred, 104.0) is None

    def test_non_numeric_atr_returns_none(self):
        pred = _long_pred()
        pred["atr"] = "not-a-number"
        assert _pts(pred, 104.0) is None

    def test_short_with_zero_legacy_stop_gets_trailed(self):
        pred = _short_pred(stop=0.0)
        new_stop = _pts(pred, 96.0)
        assert new_stop is not None and new_stop > 96.0

    def test_longs_require_stop_to_rise(self, monkeypatch):
        # trailing computed below the current stop stays None
        pred = _long_pred(entry=100.0, stop=103.9, atr=1.0)
        assert _pts(pred, 104.5) is None
