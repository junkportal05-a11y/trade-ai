"""AI Chat service with Gemini 2.0 Flash structured output & multimodal analysis."""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

from pydantic import BaseModel, Field
from app.models.schemas import ChatRequest
from app.core.config import settings


class ChatResponse(BaseModel):
    """Structured chat response from Gemini."""
    reply: str = Field(description="The mentor's response to the user")
    source: str = Field(description="Source of the response: 'gemini' or 'heuristic'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: Optional[str] = Field(default=None, description="Brief reasoning for the response")


class ChartAnalysis(BaseModel):
    """Structured chart analysis from Gemini multimodal."""
    trend: str = Field(description="Overall trend: bullish, bearish, or sideways")
    support_levels: list[float] = Field(default_factory=list, description="Key support price levels")
    resistance_levels: list[float] = Field(default_factory=list, description="Key resistance price levels")
    patterns: list[str] = Field(default_factory=list, description="Identified chart patterns")
    breakout_signal: Optional[str] = Field(default=None, description="Breakout direction if detected: up, down, or none")
    confidence: float = Field(description="Analysis confidence 0-1")
    notes: str = Field(description="Brief analytical notes")


def _analyze_chart_base64(image_b64: str, symbol: str = "") -> dict:
    """
    Multimodal analysis of a candlestick chart from base64 image data.
    Returns structured ChartAnalysis with support/resistance, patterns, and breakout signals.
    """
    if not settings.gemini_api_key:
        return {
            "trend": "unknown",
            "support_levels": [],
            "resistance_levels": [],
            "patterns": [],
            "breakout_signal": None,
            "confidence": 0.0,
            "notes": "GEMINI_API_KEY not configured — multimodal analysis unavailable",
            "source": "heuristic",
        }

    try:
        from google import genai as _genai
        client = _genai.Client(api_key=settings.gemini_api_key)

        prompt = (
            f"You are an expert technical analyst. Analyze this {symbol} candlestick chart image. "
            "Identify: 1) Overall trend (bullish/bearish/sideways), 2) Key support and resistance levels, "
            "3) Chart patterns (e.g., head and shoulders, double top/bottom, flags, triangles, wedges, "
            "cup and handle, channels), 4) Any breakout signals with direction. "
            "Return structured JSON only."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                prompt,
                {"inline_data": {"mime_type": "image/png", "data": image_b64}},
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": ChartAnalysis,
            },
        )
        parsed = ChartAnalysis.model_validate_json(response.text)
        result = parsed.model_dump()
        result["source"] = "gemini"
        return result
    except Exception as e:
        return {
            "trend": "unknown",
            "support_levels": [],
            "resistance_levels": [],
            "patterns": [],
            "breakout_signal": None,
            "confidence": 0.0,
            "notes": f"Multimodal analysis failed: {e}",
            "source": "heuristic",
        }


def analyze_chart_image(image_path: str, symbol: str = "") -> dict:
    """
    Multimodal analysis of a candlestick chart image using Gemini 2.0 Flash.
    Returns structured ChartAnalysis with support/resistance, patterns, and breakout signals.
    """
    if not settings.gemini_api_key:
        return {
            "trend": "unknown",
            "support_levels": [],
            "resistance_levels": [],
            "patterns": [],
            "breakout_signal": None,
            "confidence": 0.0,
            "notes": "GEMINI_API_KEY not configured — multimodal analysis unavailable",
            "source": "heuristic",
        }

    try:
        from google import genai as _genai
        client = _genai.Client(api_key=settings.gemini_api_key)

        # Read and encode image
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        return _analyze_chart_base64(image_b64, symbol)
    except Exception as e:
        return {
            "trend": "unknown",
            "support_levels": [],
            "resistance_levels": [],
            "patterns": [],
            "breakout_signal": None,
            "confidence": 0.0,
            "notes": f"Multimodal analysis failed: {e}",
            "source": "heuristic",
        }


def get_chat_reply(req: ChatRequest, symbol: str, price: Optional[float], chg_pct: Optional[float]) -> dict:
    gemini_reply = _get_gemini_reply(req, symbol, price, chg_pct)
    if gemini_reply:
        return gemini_reply
    return _get_heuristic_reply(req, symbol, price, chg_pct)
