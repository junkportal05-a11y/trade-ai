import os
import re
import requests
from dotenv import load_dotenv
from app.core.logging import logger

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Initialize Gemini Client if key is available
try:
    from google import genai as _genai

    _GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    if _GEMINI_KEY:
        _genai_client = _genai.Client(api_key=_GEMINI_KEY)
    else:
        _genai_client = None
except ImportError:
    _genai_client = None


def fetch_ticker_news(symbol: str) -> list[dict]:
    """
    Fetch news articles from NewsAPI for a given stock symbol.
    Returns a list of dicts: [{"title": str, "description": str, "url": str, "publishedAt": str}]
    """
    if not NEWS_API_KEY:
        return []

    # Strip suffix like .NS or .BO
    clean_sym = symbol.split(".")[0]

    # Map some common Indian tickers to specific queries to avoid search noise
    name_map = {
        "HAL": "Hindustan Aeronautics OR HAL stock",
        "BEL": "Bharat Electronics OR BEL stock",
        "RVNL": "Rail Vikas Nigam OR RVNL stock",
        "IREDA": "IREDA stock OR Indian Renewable Energy",
        "HUDCO": "HUDCO stock OR Housing and Urban Development Corporation",
        "COALINDIA": "Coal India stock",
        "NHPC": "NHPC stock",
        "ADANIPORTS": "Adani Ports stock",
        "TATAPOWER": "Tata Power stock",
        "BHEL": "BHEL stock OR Bharat Heavy Electricals",
    }

    query = name_map.get(clean_sym, f"{clean_sym} stock OR {clean_sym} share")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,  # Top 5 articles
        "apiKey": NEWS_API_KEY,
    }

    try:
        res = requests.get(url, params=params, timeout=5)
        if res.ok:
            data = res.json()
            articles = data.get("articles", [])
            return [
                {
                    "title": art.get("title", ""),
                    "description": art.get("description", ""),
                    "url": art.get("url", ""),
                    "publishedAt": art.get("publishedAt", ""),
                }
                for art in articles
                if art.get("title")
            ]
        else:
            logger.error(f"[NewsAPI] Response error: Status {res.status_code}", extra={"symbol": symbol})

    except Exception as e:
        logger.error(f"[NewsAPI] Failed to fetch news for {symbol}: {e}", extra={"symbol": symbol})

    return []


class SentimentResult:
    """Structured sentiment analysis result."""
    def __init__(self, score: float, label: str, confidence: float, source: str, reasoning: str = ""):
        self.score = score
        self.label = label
        self.confidence = confidence
        self.source = source
        self.reasoning = reasoning


def analyze_news_sentiment(articles: list[dict]) -> SentimentResult:
    """
    Evaluates the aggregate sentiment of the articles.
    Returns a SentimentResult with score, label, confidence, and source.
    """
    if not articles:
        return SentimentResult(0.0, "NEUTRAL", 1.0, "heuristic", "No articles provided")

    # 1. Try Gemini structured analysis if client is available
    if _genai_client:
        try:
            from pydantic import BaseModel, Field
            from typing import Literal

            class SentimentSchema(BaseModel):
                label: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(description="Overall sentiment label")
                confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0-1")
                reasoning: str = Field(description="Brief reasoning for the sentiment")

            headlines = "\n".join(f"- {art.get('title', '')}" for art in articles)
            prompt = (
                "You are an expert quantitative finance sentiment analyzer. "
                "Classify the overall sentiment of the following stock news headlines as BULLISH, BEARISH, or NEUTRAL. "
                "Provide confidence and brief reasoning.\n\n"
                f"Headlines:\n{headlines}"
            )
            response = _genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": SentimentSchema,
                },
            )
            parsed = SentimentSchema.model_validate_json(response.text)

            score_map = {"BULLISH": 0.8, "BEARISH": -0.8, "NEUTRAL": 0.0}
            return SentimentResult(
                score=score_map[parsed.label],
                label=parsed.label,
                confidence=parsed.confidence,
                source="gemini",
                reasoning=parsed.reasoning,
            )
        except Exception as e:
            logger.error(
                f"[NewsAPI Sentiment] Gemini analysis failed, using rule-based fallback: {e}"
            )

    # 2. Rule-based keyword density fallback
    score = 0.0
    for art in articles:
        text = (art.get("title", "") + " " + art.get("description", "")).lower()

        bullish_matches = set(_BULLISH_PAT.findall(text))
        score += len(bullish_matches) * 0.25

        bearish_matches = set(_BEARISH_PAT.findall(text))
        score -= len(bearish_matches) * 0.25

    score = max(-1.0, min(1.0, score))
    label = "BULLISH" if score > 0.2 else "BEARISH" if score < -0.2 else "NEUTRAL"
    return SentimentResult(score, label, 0.6, "heuristic", "Keyword-based analysis")


_BULLISH_KEYWORDS = [
    "profit",
    "gain",
    "rise",
    "grow",
    "deal",
    "win",
    "high",
    "success",
    "contract",
    "bullish",
    "jump",
    "surge",
    "expand",
    "order",
    "beat",
    "positive",
    "milestone",
    "acquire",
    "revenue",
    "up",
    "dividend",
]

_BEARISH_KEYWORDS = [
    "loss",
    "fall",
    "drop",
    "fell",
    "concern",
    "cut",
    "decline",
    "warn",
    "bearish",
    "slump",
    "plunge",
    "fine",
    "penalty",
    "miss",
    "negative",
    "debt",
    "shrink",
    "investigation",
    "down",
    "slashed",
]

_BULLISH_PAT = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _BULLISH_KEYWORDS) + r")\b"
)
_BEARISH_PAT = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _BEARISH_KEYWORDS) + r")\b"
)