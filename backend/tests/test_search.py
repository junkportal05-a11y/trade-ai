import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.main import app

client = TestClient(app)

def test_search_symbols_found():
    with patch("backend.main.get_angelone_feed") as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.get_instrument_token.return_value = "12345"
        mock_get_feed.return_value = mock_feed

        response = client.get("/api/search?q=reliance")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["symbol"] == "RELIANCE.NS"
        assert data["results"][0]["name"] == "RELIANCE"

        mock_feed.get_instrument_token.assert_called_once_with("RELIANCE")

def test_search_symbols_not_found():
    with patch("backend.main.get_angelone_feed") as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.get_instrument_token.return_value = None
        mock_get_feed.return_value = mock_feed

        response = client.get("/api/search?q=unknown")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 0

def test_search_symbols_with_ns_suffix():
    with patch("backend.main.get_angelone_feed") as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.get_instrument_token.return_value = "12345"
        mock_get_feed.return_value = mock_feed

        response = client.get("/api/search?q=TCS.NS")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "TCS"

        mock_feed.get_instrument_token.assert_called_once_with("TCS")

def test_search_symbols_validation_error():
    response = client.get("/api/search?q=")
    # min_length=1 should cause a 422 error
    assert response.status_code == 422
