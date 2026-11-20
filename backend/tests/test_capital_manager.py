import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from capital_manager import calculate_risk_percentage

def test_calculate_risk_percentage():
    assert calculate_risk_percentage(1000.0, "BULL") == 0.02
    assert calculate_risk_percentage(1000.0, "BEAR") == 0.01
    assert calculate_risk_percentage(1000.0, "FLAT") == 0.01
    assert calculate_risk_percentage(500.0, "BULL") == 0.02
