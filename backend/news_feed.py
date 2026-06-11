import os
import re
import requests
from dotenv import load_dotenv

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
            print(f"[NewsAPI] Response error: Status {res.status_code}")
    except Exception as e:
        print(f"[NewsAPI] Failed to fetch news for {symbol}: {e}")

    return []


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


def analyze_news_sentiment(articles: list[dict]) -> float:
    """
    Evaluates the aggregate sentiment of the articles.
    Returns a score between -1.0 (highly bearish) and +1.0 (highly bullish).
    """
    if not articles:
        return 0.0

    # 1. Try Gemini analysis if client is available
    if _genai_client:
        try:
            headlines = "\n".join(f"- {art.get('title', '')}" for art in articles)
            prompt = (
                "You are an expert quantitative finance sentiment analyzer. "
                "Classify the overall sentiment of the following stock news headlines as either BULLISH, BEARISH, or NEUTRAL. "
                "Respond with ONLY a single word: BULLISH, BEARISH, or NEUTRAL.\n\n"
                f"Headlines:\n{headlines}"
            )
            response = _genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            text = response.text.strip().upper()
            if "BULLISH" in text:
                return 0.8
            elif "BEARISH" in text:
                return -0.8
            elif "NEUTRAL" in text:
                return 0.0
        except Exception as e:
            print(
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

    return max(-1.0, min(1.0, score))
