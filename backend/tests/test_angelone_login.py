import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.security import require_session

@pytest.fixture
def override_require_session():
    app.dependency_overrides[require_session] = lambda: {"user_id": 1, "username": "test_user"}
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client(override_require_session):
    return TestClient(app)

def test_angelone_login_success(client):
    with patch('backend.main.get_angelone_feed') as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.login.return_value = {
            "status": "success",
            "session_token": "mock_session",
            "refresh_token": "mock_refresh",
            "feed_token": "mock_feed"
        }
        mock_get_feed.return_value = mock_feed

        with patch('db.save_angelone_session') as mock_save:
            payload = {
                "api_key": "test_key",
                "client_code": "test_client",
                "pin": "1234",
                "totp_secret": "test_totp"
            }

            response = client.post("/api/angelone/login", json=payload)

            assert response.status_code == 200
            assert response.json() == {"status": "success", "client_code": "test_client"}

            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]
            assert saved_data["api_key"] == "test_key"
            assert saved_data["client_code"] == "test_client"
            assert saved_data["pin"] == "1234"
            assert saved_data["totp_secret"] == "test_totp"
            assert saved_data["session_token"] == "mock_session"
            assert saved_data["refresh_token"] == "mock_refresh"
            assert saved_data["feed_token"] == "mock_feed"
            assert "updated_at" in saved_data

def test_angelone_login_failure(client):
    with patch('backend.main.get_angelone_feed') as mock_get_feed:
        mock_feed = MagicMock()
        mock_feed.login.return_value = {
            "status": "failure",
            "message": "Invalid credentials"
        }
        mock_get_feed.return_value = mock_feed

        with patch('db.save_angelone_session') as mock_save:
            payload = {
                "api_key": "test_key",
                "client_code": "test_client",
                "pin": "1234",
                "totp_secret": "test_totp"
            }

            response = client.post("/api/angelone/login", json=payload)

            assert response.status_code == 400
            assert response.json() == {"detail": "Invalid credentials"}

            mock_save.assert_not_called()
