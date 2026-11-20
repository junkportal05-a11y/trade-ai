"""TAR-19 P1-2: POST /api/chat heuristic fallback when Gemini is unconfigured or fails."""
import json
import sys
import types

from app.services.chat import get_chat_reply


def _set_key(value):
    from app.core.config import settings

    original = settings.gemini_api_key
    settings.gemini_api_key = value
    return original


POST_BODY = {
    "message": "Provide a quick recommendation for YESBANK at current price.",
    "context": {"symbol": "YESBANK", "price": 25.0, "changePct": 3.2},
    "history": [],
}


def test_chat_missing_gemini_key_returns_heuristic(auth_client):
    original = _set_key(None)
    try:
        response = auth_client.post("/api/chat", json=POST_BODY)
    finally:
        _set_key(original)
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "heuristic"
    assert "YESBANK" in data["reply"]
    assert "Heuristic read" in data["reply"]
    assert "₹24.5" in data["reply"] and "₹25.5" in data["reply"]
    assert "Gemini" not in data["reasoning"]


def test_chat_missing_priced_context_returns_honest_no_price(auth_client):
    original = _set_key(None)
    try:
        response = auth_client.post(
            "/api/chat",
            json={"message": "Any thoughts?", "context": {"symbol": "YESBANK"}, "history": []},
        )
    finally:
        _set_key(original)
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "heuristic"
    assert data["confidence"] == 0.2
    assert "no priced context" in data["reply"]


def test_chat_gemini_failure_falls_back_to_heuristic(auth_client):
    """Key configured but the model call explodes: must still 200 as heuristic."""
    original = _set_key("test-key-present")
    seen = {}

    class _FailingClient:
        def __init__(self, api_key=None):
            seen["key_present"] = bool(api_key)

        class models:
            @staticmethod
            def generate_content(*args, **kwargs):
                raise RuntimeError("api down")

    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = _FailingClient
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai
    saved = {name: sys.modules.get(name) for name in ("google", "google.genai")}
    sys.modules["google"] = fake_google
    sys.modules["google.genai"] = fake_genai
    try:
        response = auth_client.post("/api/chat", json=POST_BODY)
    finally:
        sys.modules.pop("google", None)
        sys.modules.pop("google.genai", None)
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module
        _set_key(original)

    assert response.status_code == 200
    data = response.json()
    assert seen["key_present"] is True
    assert data["source"] == "heuristic"
    assert data["reply"]


def test_chat_gemini_success_returns_gemini_source(auth_client):
    original = _set_key("test-key-present")
    payload = json.dumps(
        {
            "reply": "Momentum favours continuation above intraday support.",
            "source": "heuristic",
            "confidence": 0.8,
            "reasoning": "trend + levels",
        }
    )

    class _FakeModels:
        @staticmethod
        def generate_content(*args, **kwargs):
            class _Resp:
                text = payload

            return _Resp()

    class _FakeClient:
        def __init__(self, api_key=None):
            self.models = _FakeModels()

    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = _FakeClient
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai
    saved = {name: sys.modules.get(name) for name in ("google", "google.genai")}
    sys.modules["google"] = fake_google
    sys.modules["google.genai"] = fake_genai
    try:
        response = auth_client.post("/api/chat", json=POST_BODY)
    finally:
        sys.modules.pop("google", None)
        sys.modules.pop("google.genai", None)
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module
        _set_key(original)

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "gemini"
    assert data["reply"] == "Momentum favours continuation above intraday support."


def test_get_chat_reply_unit_no_key_no_client():
    """Direct service call with no key never touches the SDK path."""
    from app.models.schemas import ChatRequest

    original = _set_key(None)
    try:
        req = ChatRequest(
            message="rec",
            context={"symbol": "RELIANCE", "price": 2400.0, "changePct": -2.6},
        )
        result = get_chat_reply(req, "RELIANCE", 2400.0, -2.6)
    finally:
        _set_key(original)
    assert result["source"] == "heuristic"
    assert "RELIANCE" in result["reply"]
    assert result["confidence"] == 0.5
