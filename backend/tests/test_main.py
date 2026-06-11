from fastapi.testclient import TestClient
from unittest.mock import patch
from fastapi.responses import RedirectResponse

from backend.main import app

client = TestClient(app)

@patch("backend.main.upstox_callback")
def test_upstox_callback_alias(mock_upstox_callback):
    """Test that upstox_callback_alias properly forwards to upstox_callback"""
    # Setup mock return value
    mock_response = RedirectResponse(url="/account")
    mock_upstox_callback.return_value = mock_response

    # Make request
    _ = client.get("/auth/callback?code=testcode&state=teststate")

    # Assert correct parameters were passed to upstox_callback
    args, kwargs = mock_upstox_callback.call_args
    assert kwargs["code"] == "testcode"
    assert kwargs["state"] == "teststate"
    assert "request" in kwargs
