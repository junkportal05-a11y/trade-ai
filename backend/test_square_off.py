import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import trading_agent

@patch('trading_agent.db')
@patch('trading_agent.get_angelone_feed')
def test_square_off_uses_live_price(mock_get_feed, mock_db):
    mock_db.get_predictions.return_value = [
        {"id": 1, "symbol": "TCS-EQ", "status": "PENDING", "prediction_type": "BUY", "entry_price": 100.0, "position_size": 10}
    ]
    # Provide a live quote
    mock_feed = MagicMock()
    mock_feed.is_authorized.return_value = True
    mock_feed.get_live_quotes.return_value = {"TCS-EQ": {"price": 110.0}}
    mock_get_feed.return_value = mock_feed
    
    now_ist = datetime.now(timezone.utc)
    trading_agent._square_off_all(now_ist)
    
    # Assert resolve_prediction was called with 110.0
    mock_db.resolve_prediction.assert_called_once()
    args, kwargs = mock_db.resolve_prediction.call_args
    assert kwargs["actual_outcome"] == 110.0
    assert kwargs["exit_price"] == 110.0
    assert kwargs["pnl_inr"] == 100.0 # (110 - 100) * 10
    assert kwargs["pnl_pct"] == 10.0

@patch('trading_agent.db')
@patch('trading_agent.get_angelone_feed')
def test_square_off_falls_back_on_failure(mock_get_feed, mock_db):
    mock_db.get_predictions.return_value = [
        {"id": 2, "symbol": "RELIANCE-EQ", "status": "PENDING", "prediction_type": "SELL", "entry_price": 100.0, "position_size": 5}
    ]
    # Fail to get a quote
    mock_feed = MagicMock()
    mock_feed.is_authorized.return_value = True
    mock_feed.get_live_quotes.return_value = {} # Empty dict returned
    mock_get_feed.return_value = mock_feed
    
    now_ist = datetime.now(timezone.utc)
    trading_agent._square_off_all(now_ist)
    
    # Assert resolve_prediction was called with entry_price 100.0
    mock_db.resolve_prediction.assert_called_once()
    args, kwargs = mock_db.resolve_prediction.call_args
    assert kwargs["actual_outcome"] == 100.0
    assert kwargs["exit_price"] == 100.0
    assert kwargs["pnl_inr"] == 0.0
    assert kwargs["pnl_pct"] == 0.0
