import pytest
from unittest.mock import patch
import pandas as pd


@pytest.fixture(autouse=True)
def _patch_download(monkeypatch):
    """Ensure signals.download_market_data_df is patchable."""
    import signals
    monkeypatch.setattr(signals, 'download_market_data_df', lambda *a, **kw: None)


@patch('signals.download_market_data_df')
def test_get_history_valid(mock_download, auth_client):
    dates = pd.date_range("2023-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [95.0, 96.0],
            "Close": [102.0, 103.0],
            "Volume": [1000, 1500]
        },
        index=dates
    )
    mock_download.return_value = df
    response = auth_client.get("/api/history?symbol=RELIANCE&interval=1d&range=1mo")
    assert response.status_code == 200


def test_get_history_invalid_interval(auth_client):
    response = auth_client.get("/api/history?symbol=RELIANCE&interval=invalid&range=1mo")
    assert response.status_code == 400
    assert "Invalid interval" in response.json()["detail"]


def test_get_history_invalid_range(auth_client):
    response = auth_client.get("/api/history?symbol=RELIANCE&interval=1d&range=invalid")
    assert response.status_code == 400
    assert "Invalid range" in response.json()["detail"]


def test_get_history_missing_symbol(auth_client):
    response = auth_client.get("/api/history?interval=1d&range=1mo")
    assert response.status_code == 422


@patch('signals.download_market_data_df')
def test_get_history_empty_data(mock_download, auth_client):
    mock_download.return_value = pd.DataFrame()
    response = auth_client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["count"] > 0


@patch('signals.download_market_data_df')
def test_get_history_none_data(mock_download, auth_client):
    mock_download.return_value = None
    response = auth_client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["count"] > 0


@patch('signals.download_market_data_df')
def test_get_history_nan_data(mock_download, auth_client):
    mock_download.return_value = pd.DataFrame({'Open': [float('nan')], 'High': [float('nan')], 'Low': [float('nan')], 'Close': [float('nan')], 'Volume': [float('nan')]})
    response = auth_client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["count"] > 0


@patch('signals.download_market_data_df')
def test_get_history_intraday(mock_download, auth_client):
    dates = pd.date_range("2023-01-01 10:00:00", periods=2, freq="15min")
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [95.0, 96.0],
            "Close": [102.0, 103.0],
            "Volume": [1000, 1500]
        },
        index=dates
    )
    mock_download.return_value = df

    response = auth_client.get("/api/history?symbol=RELIANCE&interval=15m&range=1d")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "RELIANCE"
    assert data["interval"] == "15m"
    assert data["range"] == "1d"
    assert data["count"] == 2

    assert isinstance(data["bars"][0]["time"], int)
    assert data["bars"][0]["time"] == int(dates[0].timestamp())
    assert data["bars"][0]["open"] == 100.0
    assert data["bars"][0]["volume"] == 1000


@patch('signals.download_market_data_df')
def test_get_history_daily(mock_download, auth_client):
    dates = pd.date_range("2023-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [95.0, 96.0],
            "Close": [102.0, 103.0],
            "Volume": [1000, 1500]
        },
        index=dates
    )
    mock_download.return_value = df

    response = auth_client.get("/api/history?symbol=RELIANCE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2

    assert isinstance(data["bars"][0]["time"], str)
    assert data["bars"][0]["time"] == "2023-01-01"


def _multiindex_ohlcv(dates) -> pd.DataFrame:
    cols = pd.MultiIndex.from_tuples(
        [
            ("open", "RELIANCE.NS"),
            ("high", "RELIANCE.NS"),
            ("low", "RELIANCE.NS"),
            ("close", "RELIANCE.NS"),
            ("volume", "RELIANCE.NS"),
        ]
    )
    return pd.DataFrame(
        [
            [100.0, 105.0, 95.0, 102.0, 1000],
            [101.0, 106.0, 96.0, 103.0, 1500],
        ],
        index=dates,
        columns=cols,
    )


@patch('signals.download_market_data_df')
def test_get_history_multiindex_flattened(mock_download, auth_client):
    dates = pd.date_range("2023-01-01", periods=2, freq="D")
    mock_download.return_value = _multiindex_ohlcv(dates)

    response = auth_client.get("/api/history?symbol=RELIANCE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["bars"][0]["open"] == 100.0
    assert data["bars"][0]["close"] == 102.0
    assert data["bars"][0]["volume"] == 1000
    assert data["data_source"] is None  # patched chain carries no tier record


@patch('signals.download_market_data_df')
def test_get_history_data_source_from_feed_tier(mock_download, auth_client):
    import signals
    dates = pd.date_range("2023-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [95.0, 96.0],
            "Close": [102.0, 103.0],
            "Volume": [1000, 1500]
        },
        index=dates
    )
    mock_download.return_value = df
    cache_key = "TCS_1d"
    signals._SOURCE_CACHE[cache_key] = "yfinance"
    try:
        response = auth_client.get("/api/history?symbol=TCS&interval=1d&range=1mo")
    finally:
        signals._SOURCE_CACHE.pop(cache_key, None)

    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is False
    assert data["data_source"] == "yfinance"


@patch('signals.download_market_data_df')
def test_get_history_data_source_synthetic_after_fallback(mock_download, auth_client):
    mock_download.return_value = pd.DataFrame()
    response = auth_client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert data["data_source"] == "synthetic"


@patch('app.api.v1.quotes.generate_synthetic_candles')
@patch('signals.download_market_data_df')
def test_get_history_503_when_nothing_available(mock_download, mock_synth, auth_client):
    mock_download.return_value = None
    mock_synth.return_value = None
    response = auth_client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 503
    assert "retry" in response.json()["detail"].lower()
