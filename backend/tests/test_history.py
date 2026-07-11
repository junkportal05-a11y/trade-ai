import pytest
from fastapi.testclient import TestClient
import pandas as pd
import datetime
import numpy as np

from app.main import app
import backend.signals as sig_engine

client = TestClient(app)

def test_get_history_happy_path_daily(monkeypatch):
    """Test daily interval, checking date is returned as string 'YYYY-MM-DD'"""
    def mock_download(*args, **kwargs):
        index = pd.DatetimeIndex([datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2)])
        data = {
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000, 2000]
        }
        return pd.DataFrame(data, index=index)

    monkeypatch.setattr("backend.main.sig_engine.download_market_data_df", mock_download)

    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1d", "range": "5d"})
    assert response.status_code == 200

    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["interval"] == "1d"
    assert data["range"] == "5d"
    assert data["count"] == 2

    bars = data["bars"]
    assert len(bars) == 2
    assert bars[0]["time"] == "2023-01-01"
    assert bars[1]["time"] == "2023-01-02"
    assert bars[0]["open"] == 100.0
    assert bars[0]["high"] == 102.0
    assert bars[0]["low"] == 99.0
    assert bars[0]["close"] == 101.0
    assert bars[0]["volume"] == 1000

def test_get_history_happy_path_intraday(monkeypatch):
    """Test intraday interval, checking date is returned as Unix timestamp"""
    def mock_download(*args, **kwargs):
        index = pd.DatetimeIndex([datetime.datetime(2023, 1, 1, 10, 30, tzinfo=datetime.timezone.utc), datetime.datetime(2023, 1, 1, 10, 31, tzinfo=datetime.timezone.utc)])
        data = {
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000, 2000]
        }
        return pd.DataFrame(data, index=index)

    monkeypatch.setattr("backend.main.sig_engine.download_market_data_df", mock_download)

    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1m", "range": "1d"})
    assert response.status_code == 200

    data = response.json()
    assert data["interval"] == "1m"
    assert data["count"] == 2

    bars = data["bars"]
    assert len(bars) == 2
    # Expect integer unix timestamp
    assert isinstance(bars[0]["time"], int)
    assert bars[0]["time"] == int(datetime.datetime(2023, 1, 1, 10, 30, tzinfo=datetime.timezone.utc).timestamp())
    assert bars[1]["time"] == int(datetime.datetime(2023, 1, 1, 10, 31, tzinfo=datetime.timezone.utc).timestamp())

def test_get_history_invalid_interval():
    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "invalid_int", "range": "1mo"})
    assert response.status_code == 400
    assert "Invalid interval" in response.json()["detail"]

def test_get_history_invalid_range():
    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1d", "range": "invalid_range"})
    assert response.status_code == 400
    assert "Invalid range" in response.json()["detail"]

def test_get_history_no_data(monkeypatch):
    """Test when sig_engine returns None"""
    def mock_download(*args, **kwargs):
        return None

    monkeypatch.setattr("backend.main.sig_engine.download_market_data_df", mock_download)

    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1d", "range": "1mo"})
    assert response.status_code == 404
    assert "No history for AAPL" in response.json()["detail"]

def test_get_history_empty_df(monkeypatch):
    """Test when sig_engine returns an empty DataFrame"""
    def mock_download(*args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr("backend.main.sig_engine.download_market_data_df", mock_download)

    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1d", "range": "1mo"})
    assert response.status_code == 404
    assert "No history for AAPL" in response.json()["detail"]

def test_get_history_nan_filtering(monkeypatch):
    """Test that rows with NaN in OHLC are dropped"""
    def mock_download(*args, **kwargs):
        index = pd.DatetimeIndex([datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2), datetime.datetime(2023, 1, 3)])
        data = {
            'Open': [100.0, np.nan, 102.0],
            'High': [102.0, 103.0, np.nan],
            'Low': [99.0, 100.0, 101.0],
            'Close': [101.0, 102.0, 103.0],
            'Volume': [1000, 2000, 3000]
        }
        return pd.DataFrame(data, index=index)

    monkeypatch.setattr("backend.main.sig_engine.download_market_data_df", mock_download)

    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1d", "range": "5d"})
    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 1
    bars = data["bars"]
    assert len(bars) == 1
    # Only the first row (2023-01-01) should remain, others have NaNs in Open or High
    assert bars[0]["time"] == "2023-01-01"

def test_get_history_nan_filtering_all_nan(monkeypatch):
    """Test that rows with NaN are dropped and returns 404 if resulting df is empty"""
    def mock_download(*args, **kwargs):
        index = pd.DatetimeIndex([datetime.datetime(2023, 1, 1)])
        data = {
            'Open': [np.nan],
            'High': [102.0],
            'Low': [99.0],
            'Close': [101.0],
            'Volume': [1000]
        }
        return pd.DataFrame(data, index=index)

    monkeypatch.setattr("backend.main.sig_engine.download_market_data_df", mock_download)

    response = client.get("/api/history", params={"symbol": "AAPL", "interval": "1d", "range": "5d"})
    assert response.status_code == 404
    assert "No history data found for AAPL after filtering NaNs" in response.json()["detail"]
