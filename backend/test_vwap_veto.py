import pytest
from signals import vwap_veto

def test_buy_above_vwap_passes():
    assert vwap_veto(price=105, vwap=100, direction="BUY") == (True, None)

def test_buy_below_vwap_vetoed():
    passed, reason = vwap_veto(price=95, vwap=100, direction="BUY")
    assert passed == False
    assert "VETO" in reason

def test_sell_below_vwap_passes():
    assert vwap_veto(price=95, vwap=100, direction="SELL") == (True, None)

def test_sell_above_vwap_vetoed():
    passed, reason = vwap_veto(price=105, vwap=100, direction="SELL")
    assert passed == False
    assert "VETO" in reason
