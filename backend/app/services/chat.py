"""AI Chat service."""
from __future__ import annotations

import os
from typing import Optional

from app.models.schemas import ChatRequest
from app.core.config import settings


def _get_heuristic_reply(req: ChatRequest, symbol: str, price: Optional[float], chg_pct: Optional[float]) -> dict:
    """Fallback heuristic engine when Gemini is unavailable."""
    msg_lower = req.message.lower()
    price_str = f"₹{price:,.2f}" if price else "current levels"
    chg_str = f"{chg_pct:+.2f}%" if chg_pct is not None else "unchanged"

    responses = {
        "hammer": (
            "**Hammer Candlestick** — A bullish reversal pattern. Small body at the top with a long lower shadow (≥2x body). "
            "Confirmation requires a close above the hammer's body. *(Local fallback — set GEMINI_API_KEY for AI mentoring)*"
        ),
        "doji": (
            "**Doji Candlestick** — Market equilibrium. Dragonfly Doji = bullish rejection; Gravestone = bearish rejection. "
            "*(Local fallback — set GEMINI_API_KEY for AI mentoring)*"
        ),
        "engulfing": (
            "**Engulfing Pattern** — A large candle wrapping the previous one. Bullish = buyers took control. "
            "*(Local fallback — set GEMINI_API_KEY for AI mentoring)*"
        ),
        "candlestick": (
            "**Candlestick Patterns** — Visual maps of price. Seek confluence with support/resistance and volume expansion. "
            "*(Local fallback — set GEMINI_API_KEY for AI mentoring)*"
        ),
        "rsi": (
            "**RSI** — Momentum oscillator 0-100. >70 = overbought; <30 = oversold. *(Local fallback)*"
        ),
        "macd": (
            "**MACD** — Trend-following momentum. Crossover above signal = bullish. Divergence warns reversals. *(Local fallback)*"
        ),
    }

    for key, reply in responses.items():
        if key in msg_lower:
            return {"reply": reply, "source": "heuristic"}

    if any(w in msg_lower for w in ["buy", "long", "bullish"]):
        reply = (
            f"**{symbol} Bull Case** — At {price_str} ({chg_str}), accumulate on dips. "
            "Watch for volume confirmation on breakouts. Set SL below recent swing low."
        )
    elif any(w in msg_lower for w in ["sell", "short", "bearish"]):
        reply = (
            f"**{symbol} Bear Case** — At {price_str}, if price breaks key support with volume, "
            "path may be lower. Use defined risk limits."
        )
    elif any(w in msg_lower for w in ["price", "target", "value"]):
        reply = (
            f"**{symbol}** is at {price_str} ({chg_str}). Use technical levels or DCF for targets."
        )
    elif any(w in msg_lower for w in ["risk", "stop", "position"]):
        reply = (
            f"**Risk Management** — Never risk >1-2% per trade. Position size = (Capital × 0.01) / (Entry - SL)."
        )
    else:
        reply = (
            f"**{symbol}** @ {price_str} ({chg_str}) — Ask about signals, risk, or catalysts. "
            "💡 Tip: Set GEMINI_API_KEY for real AI responses."
        )

    return {"reply": reply, "source": "heuristic"}


def _get_gemini_reply(req: ChatRequest, symbol: str, price: Optional[float], chg_pct: Optional[float]) -> Optional[dict]:
    """Attempts to get a reply from Gemini AI."""
    if not settings.gemini_api_key:
        return None

    try:
        from google import genai as _genai
        client = _genai.Client(api_key=settings.gemini_api_key)

        knowledge_content = ""
        knowledge_path = os.path.join(os.path.dirname(__file__), "..", "..", "trading_knowledge.txt")
        if os.path.exists(knowledge_path):
            with open(knowledge_path, "r", encoding="utf-8") as kf:
                knowledge_content = kf.read(140000)

        news_context = ""
        if symbol and symbol != "the market":
            try:
                import sys
                import os
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                from news_feed import fetch_ticker_news
                articles = fetch_ticker_news(symbol)
                if articles:
                    news_context = "--- LATEST NEWS ---\n"
                    for art in articles[:3]:
                        news_context += f"• {art.get('title')} ({art.get('publishedAt', '')[:10]})\n"
                    news_context += "\n"
            except Exception:
                pass

        system_ctx = (
            f"You are an expert trading mentor in ApexTrade. "
            f"Use knowledge context to answer trading queries.\n\n"
            f"--- KNOWLEDGE ---\n{knowledge_content}\n---\n\n"
            f"{news_context}"
            f"Active: {symbol}"
            + (f" @ ₹{price:.2f}" if price else "")
            + (f" ({chg_pct:+.2f}%)" if chg_pct is not None else "")
            + ". Keep under 180 words. Use **bold** sparingly."
        )

        formatted_history = ""
        if req.history:
            for h in req.history:
                role = "User" if h.role == "user" else "Assistant"
                formatted_history += f"{role}: {h.text}\n"

        prompt = f"{system_ctx}\n\n{formatted_history}User: {req.message}\nAssistant:"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return {"reply": response.text.strip(), "source": "gemini"}
    except Exception:
        return None


def get_chat_reply(req: ChatRequest, symbol: str, price: Optional[float], chg_pct: Optional[float]) -> dict:
    gemini_reply = _get_gemini_reply(req, symbol, price, chg_pct)
    if gemini_reply:
        return gemini_reply
    return _get_heuristic_reply(req, symbol, price, chg_pct)
