from fastapi.testclient import TestClient
from unittest.mock import patch
import pandas as pd
from backend.main import app

client = TestClient(app)

@patch('signals.download_market_data_df')
def test_get_history_valid(mock_download):
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
    response = client.get("/api/history?symbol=RELIANCE&interval=1d&range=1mo")
    assert response.status_code == 200

def test_get_history_invalid_interval():
    response = client.get("/api/history?symbol=RELIANCE&interval=invalid&range=1mo")
    assert response.status_code == 400
    assert "Invalid interval" in response.json()["detail"]

def test_get_history_invalid_range():
    response = client.get("/api/history?symbol=RELIANCE&interval=1d&range=invalid")
    assert response.status_code == 400
    assert "Invalid range" in response.json()["detail"]

def test_get_history_missing_symbol():
    response = client.get("/api/history?interval=1d&range=1mo")
    assert response.status_code == 422

@patch('signals.download_market_data_df')
def test_get_history_empty_data(mock_download):
    mock_download.return_value = pd.DataFrame()
    response = client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 404
    assert "No history for FAKE" in response.json()["detail"]

@patch('signals.download_market_data_df')
def test_get_history_none_data(mock_download):
    mock_download.return_value = None
    response = client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 404
    assert "No history for FAKE" in response.json()["detail"]

@patch('signals.download_market_data_df')
def test_get_history_nan_data(mock_download):
    mock_download.return_value = pd.DataFrame({'Open': [float('nan')], 'High': [float('nan')], 'Low': [float('nan')], 'Close': [float('nan')], 'Volume': [float('nan')]})
    response = client.get("/api/history?symbol=FAKE&interval=1d&range=1mo")
    assert response.status_code == 404
    assert "No history data found for FAKE after filtering NaNs" in response.json()["detail"]

@patch('signals.download_market_data_df')
def test_get_history_intraday(mock_download):
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

    response = client.get("/api/history?symbol=RELIANCE&interval=15m&range=1d")
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
def test_get_history_daily(mock_download):
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

    response = client.get("/api/history?symbol=RELIANCE&interval=1d&range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2

    assert isinstance(data["bars"][0]["time"], str)
    assert data["bars"][0]["time"] == "2023-01-01"
