import pytest
from backend.signals import validate_risk_reward


@pytest.mark.parametrize(
    "entry, stop, target, min_rr, expected",
    [
        # Zero risk (entry == stop)
        (100.0, 100.0, 110.0, 2.0, False),
        # Long trade passes (Risk: 5, Reward: 10, R:R: 2.0)
        (100.0, 95.0, 110.0, 2.0, True),
        # Long trade passes (Risk: 5, Reward: 15, R:R: 3.0)
        (100.0, 95.0, 115.0, 2.0, True),
        # Long trade fails (Risk: 5, Reward: 5, R:R: 1.0)
        (100.0, 95.0, 105.0, 2.0, False),
        # Short trade passes (Risk: 5, Reward: 10, R:R: 2.0)
        (100.0, 105.0, 90.0, 2.0, True),
        # Short trade passes (Risk: 5, Reward: 15, R:R: 3.0)
        (100.0, 105.0, 85.0, 2.0, True),
        # Short trade fails (Risk: 5, Reward: 5, R:R: 1.0)
        (100.0, 105.0, 95.0, 2.0, False),
        # Custom min_rr
        # Risk: 5, Reward: 5, R:R: 1.0 >= 1.0
        (100.0, 95.0, 105.0, 1.0, True),
        # Risk: 5, Reward: 10, R:R: 2.0 < 3.0
        (100.0, 95.0, 110.0, 3.0, False),
        # Risk: 5, Reward: 15, R:R: 3.0 >= 3.0
        (100.0, 95.0, 115.0, 3.0, True),
    ],
)
def test_validate_risk_reward(entry, stop, target, min_rr, expected):
    assert validate_risk_reward(entry, stop, target, min_rr) == expected


def test_validate_risk_reward_default_min_rr():
    # Long trade with 1:2 R:R (passes default min_rr=2.0)
    assert validate_risk_reward(100.0, 95.0, 110.0) is True
    # Long trade with 1:1.5 R:R (fails default min_rr=2.0)
    assert validate_risk_reward(100.0, 95.0, 107.5) is False
