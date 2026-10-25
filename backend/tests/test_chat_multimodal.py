"""Tests for multimodal chart analysis endpoint."""
import base64
import pytest
from unittest.mock import patch

# 1x1 transparent PNG base64 for testing
TEST_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def test_analyze_chart_json_missing_image_base64(auth_client):
    """Test JSON endpoint with missing image_base64 returns 422 (validation error)."""
    response = auth_client.post("/api/chat/chart", json={"symbol": "NIFTY"})
    assert response.status_code == 422  # FastAPI validation error for missing required field


def test_analyze_chart_json_valid(auth_client):
    """Test JSON endpoint with valid base64 returns 200 with structured response."""
    with patch("app.services.chat._analyze_chart_base64") as mock_analyze:
        mock_analyze.return_value = {
            "trend": "bullish",
            "support_levels": [19500.0, 19300.0],
            "resistance_levels": [20000.0, 20200.0],
            "patterns": ["ascending_triangle"],
            "breakout_signal": "up",
            "confidence": 0.85,
            "notes": "Strong uptrend with clear ascending triangle pattern",
            "source": "gemini",
        }
        response = auth_client.post(
            "/api/chat/chart",
            json={"image_base64": TEST_IMAGE_B64, "symbol": "NIFTY"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["trend"] == "bullish"
    assert data["support_levels"] == [19500.0, 19300.0]
    assert data["resistance_levels"] == [20000.0, 20200.0]
    assert data["patterns"] == ["ascending_triangle"]
    assert data["breakout_signal"] == "up"
    assert data["confidence"] == 0.85
    assert data["source"] == "gemini"


def test_analyze_chart_upload_no_file(auth_client):
    """Test file upload endpoint with no file returns 422."""
    response = auth_client.post("/api/chat/chart/upload")
    assert response.status_code == 422  # FastAPI validation error for missing file


def test_analyze_chart_upload_valid(auth_client):
    """Test file upload endpoint with valid PNG returns 200."""
    test_file = base64.b64decode(TEST_IMAGE_B64)
    with patch("app.services.chat._analyze_chart_base64") as mock_analyze:
        mock_analyze.return_value = {
            "trend": "sideways",
            "support_levels": [18000.0],
            "resistance_levels": [18500.0],
            "patterns": ["rectangle"],
            "breakout_signal": "none",
            "confidence": 0.7,
            "notes": "Range-bound consolidation",
            "source": "gemini",
        }
        response = auth_client.post(
            "/api/chat/chart/upload",
            files={"file": ("chart.png", test_file, "image/png")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["trend"] == "sideways"
    assert data["patterns"] == ["rectangle"]
    assert data["breakout_signal"] == "none"


def test_analyze_chart_upload_invalid_type(auth_client):
    """Test file upload with invalid content type returns 400."""
    test_file = b"not an image"
    response = auth_client.post(
        "/api/chat/chart/upload",
        files={"file": ("chart.txt", test_file, "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PNG/JPEG images supported" in response.json()["detail"]


def test_analyze_chart_upload_too_large(auth_client):
    """Test file upload with file > 10MB returns 400."""
    # Create a file larger than 10MB
    large_file = b"x" * (11 * 1024 * 1024)
    response = auth_client.post(
        "/api/chat/chart/upload",
        files={"file": ("large.png", large_file, "image/png")}
    )
    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


def test_analyze_chart_missing_gemini_key(auth_client):
    """Test endpoint gracefully handles missing GEMINI_API_KEY."""
    # This test relies on the actual service fallback since we don't mock settings
    # The service should return heuristic response when key is missing
    from app.core.config import settings
    original_key = settings.gemini_api_key
    try:
        settings.gemini_api_key = None
        response = auth_client.post(
            "/api/chat/chart",
            json={"image_base64": TEST_IMAGE_B64, "symbol": "NIFTY"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "heuristic"
        assert data["trend"] == "unknown"
        assert "GEMINI_API_KEY not configured" in data["notes"]
    finally:
        settings.gemini_api_key = original_key