import pytest
import pandas as pd
from quant.correlation_matrix import CorrelationEngine

def test_correlation_engine_blocks_correlated():
    engine = CorrelationEngine()
    # Mock the correlation matrix
    engine.correlation_matrix = pd.DataFrame({
        "HDFCBANK.NS": {"HDFCBANK.NS": 1.0, "ICICIBANK.NS": 0.90},
        "ICICIBANK.NS": {"HDFCBANK.NS": 0.90, "ICICIBANK.NS": 1.0}
    })
    engine.matrix_build_failed = False
    
    # Try to buy ICICI when holding HDFC
    allowed = engine.check_trade_allowed("ICICIBANK.NS", ["HDFCBANK.NS"])
    assert allowed == False

def test_correlation_engine_allows_uncorrelated():
    engine = CorrelationEngine()
    # Mock the correlation matrix
    engine.correlation_matrix = pd.DataFrame({
        "HDFCBANK.NS": {"HDFCBANK.NS": 1.0, "TCS.NS": 0.10},
        "TCS.NS": {"HDFCBANK.NS": 0.10, "TCS.NS": 1.0}
    })
    engine.matrix_build_failed = False
    
    # Try to buy TCS when holding HDFC
    allowed = engine.check_trade_allowed("TCS.NS", ["HDFCBANK.NS"])
    assert allowed == True

def test_correlation_engine_empty_portfolio_allowed():
    engine = CorrelationEngine()
    engine.correlation_matrix = pd.DataFrame({
        "HDFCBANK.NS": {"HDFCBANK.NS": 1.0}
    })
    engine.matrix_build_failed = False
    
    allowed = engine.check_trade_allowed("HDFCBANK.NS", [])
    assert allowed == True

def test_correlation_engine_fail_open_fallback():
    engine = CorrelationEngine()
    # matrix is None, build fails
    engine.matrix_build_failed = True
    
    allowed = engine.check_trade_allowed("HDFCBANK.NS", ["ICICIBANK.NS"])
    assert allowed == True
