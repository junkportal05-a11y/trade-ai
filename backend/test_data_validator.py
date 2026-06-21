import pytest
from data_validator import calculate_confidence_from_counts

def test_confidence_calculation():
    # Mock 100 trades, 85 valid
    score = calculate_confidence_from_counts(valid=85, total=100)
    assert score == 85.0

def test_confidence_zero_trades_does_not_crash():
    score = calculate_confidence_from_counts(valid=0, total=0)
    assert score == 0.0  # not a divide-by-zero crash
