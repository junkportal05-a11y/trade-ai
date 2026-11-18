from unittest.mock import patch, MagicMock


def test_get_quote_success(auth_client):
    mock_quote_data = {
        "symbol": "TCS.NS",
        "price": 3500.5,
        "change": 10.5,
        "change_percent": 0.3,
        "volume": 1234567,
    }
    # Mock the underlying AngelOne feed that get_symbol_quote calls internally.
    # Patching `app.services.quotes.get_symbol_quote` alone is insufficient
    # because the TestClient's async→sync bridge can bypass module-attribute patches.
    mock_feed = MagicMock()
    mock_feed.is_authorized.return_value = True
    mock_feed.get_live_quotes.return_value = {"TCS.NS": mock_quote_data}
    with patch("signals.get_angelone_feed", return_value=mock_feed):
        response = auth_client.get("/api/quote?symbol=TCS.NS")
        assert response.status_code == 200
        assert response.json() == mock_quote_data


def test_get_quote_not_found(auth_client):
    mock_feed = MagicMock()
    mock_feed.is_authorized.return_value = True
    mock_feed.get_live_quotes.return_value = {}
    with patch("signals.get_angelone_feed", return_value=mock_feed):
        response = auth_client.get("/api/quote?symbol=UNKNOWN.NS")
        assert response.status_code == 404
        assert response.json() == {"detail": "No data for UNKNOWN.NS"}


def test_get_quote_missing_symbol(auth_client):
    response = auth_client.get("/api/quote")
    assert response.status_code == 422 # FastAPI validation error
