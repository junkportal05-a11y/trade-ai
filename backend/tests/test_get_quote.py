import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_get_quote_success():
    mock_quote_data = {
        "symbol": "TCS.NS",
        "price": 3500.5,
        "change": 10.5,
        "change_percent": 0.3,
        "volume": 1234567,
    }
    with patch("backend.main.sig_engine.get_symbol_quote", return_value=mock_quote_data) as mock_get_quote:
        response = client.get("/api/quote?symbol=TCS.NS")
        assert response.status_code == 200
        assert response.json() == mock_quote_data
        mock_get_quote.assert_called_once_with("TCS.NS")

def test_get_quote_not_found():
    with patch("backend.main.sig_engine.get_symbol_quote", return_value=None) as mock_get_quote:
        response = client.get("/api/quote?symbol=UNKNOWN")
        assert response.status_code == 404
        assert response.json() == {"detail": "No data for UNKNOWN"}
        mock_get_quote.assert_called_once_with("UNKNOWN")

def test_get_quote_missing_symbol():
    response = client.get("/api/quote")
    assert response.status_code == 422 # FastAPI validation error
