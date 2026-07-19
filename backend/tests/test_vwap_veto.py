import pytest
from backend.signals import vwap_veto

@pytest.mark.parametrize(
    "price, vwap, direction, expected_passed, expected_reason",
    [
        # Empty direction
        (100.0, 100.0, "", True, None),
        (100.0, 100.0, None, True, None),

        # Bullish/Buy
        (90.0, 100.0, "BUY", False, "VETO: Bullish signal but price is below VWAP"),
        (90.0, 100.0, "BULLISH", False, "VETO: Bullish signal but price is below VWAP"),
        (110.0, 100.0, "buy", True, None),
        (100.0, 100.0, "BULLISH", True, None),
        (100.0, 100.0, "BUY", True, None), # price == vwap

        # Bearish/Sell
        (110.0, 100.0, "SELL", False, "VETO: Bearish signal but price is above VWAP"),
        (110.0, 100.0, "BEARISH", False, "VETO: Bearish signal but price is above VWAP"),
        (90.0, 100.0, "sell", True, None),
        (100.0, 100.0, "BEARISH", True, None),
        (100.0, 100.0, "SELL", True, None), # price == vwap

        # Unknown direction
        (90.0, 100.0, "UNKNOWN", True, None),
    ]
)
def test_vwap_veto(price, vwap, direction, expected_passed, expected_reason):
    passed, reason = vwap_veto(price, vwap, direction)
    assert passed == expected_passed
    assert reason == expected_reason
