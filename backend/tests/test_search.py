import pytest
from unittest.mock import patch, MagicMock


def test_search_symbols_found(auth_client):
    with patch("app.services.broker.get_broker_feed") as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.get_instrument_token.return_value = "12345"
        mock_get_feed.return_value = mock_feed

        response = auth_client.get("/api/search?q=RELIANCE.NS")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["symbol"] == "RELIANCE.NS"


def test_search_symbols_not_found(auth_client):
    with patch("app.services.broker.get_broker_feed") as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.get_instrument_token.return_value = None
        mock_get_feed.return_value = mock_feed

        response = auth_client.get("/api/search?q=UNKNOWN.NS")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 0


def test_search_symbols_with_ns_suffix(auth_client):
    with patch("app.services.broker.get_broker_feed") as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.get_instrument_token.return_value = "12345"
        mock_get_feed.return_value = mock_feed

        response = auth_client.get("/api/search?q=TCS.NS")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1


def test_search_symbols_validation_error(auth_client):
    response = auth_client.get("/api/search?q=")
    assert response.status_code == 422
