"""
Trading Platform Backend - FastAPI
Run with: uvicorn main:app --reload --port 8000
"""

import os
import time
import json
import random
import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import (
    Response,
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Query,
    Request,
    Depends,
    Header,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel

import signals as sig_engine
import upstox_feed
import db
import capital_allocator
from backtest_routes import backtest_router
from auth_helpers import require_admin
from historical_simulator import run_simulation_task, simulation_status

load_dotenv()


limiter = Limiter(key_func=get_remote_address)

def get_user_or_ip(request: Request) -> str:
    token = request.headers.get("x-session-token")
    if token:
        return f"user:{token}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_or_ip)

app = FastAPI(title="ApexTrade API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000,https://trade-ai-beta.vercel.app,https://frontend-two-tau-82.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from auth_helpers import (
    require_session,
    create_session,
    ACTIVE_SESSIONS,
    SESSION_TTL,
    authenticate_user,
)

# Optional Gemini AI integration (google-genai SDK)
try:
    from google import genai as _genai

    _GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    if _GEMINI_KEY:
        _genai_client = _genai.Client(api_key=_GEMINI_KEY)
    else:
        _genai_client = None
except ImportError:
    _genai_client = None

app.include_router(backtest_router)


# ── Active WebSocket connections ───────────────────────────────────────────────
active_connections: list[WebSocket] = []


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
@limiter.limit("10/minute")
async def login(req: LoginRequest, request: Request, response: Response):
    from auth_helpers import authenticate_by_code
    
    u = req.username.strip()
    p = req.password.strip()
    
    # Check if a single access code is sent (no username or generic username)
    if not u or u.lower() in ("code", "login", "admin", "apex_head_quant"):
        matched_user, user_obj = authenticate_by_code(p)
        if matched_user:
            u = matched_user
        else:
            # Try to authenticate standard admin fallback
            user_obj = authenticate_user("apex_head_quant", p)
            if user_obj:
                u = "apex_head_quant"
    else:
        user_obj = authenticate_user(u, p)
        
    if not user_obj:
        raise HTTPException(status_code=401, detail="Invalid access code or credentials")

    token = create_session(u)
    response.set_cookie(
        key="apt_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=SESSION_TTL,
    )
    return {
        "token": token,
        "username": u,
        "role": user_obj["role"],
        "clearance": user_obj["clearance"],
        "expires_in": SESSION_TTL,
    }


@app.post("/api/logout")
async def logout(request: Request, response: Response):
    x_session_token = request.cookies.get("apt_token")
    if x_session_token and x_session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[x_session_token]
    response.delete_cookie(
        key="apt_token",
        httponly=True,
        secure=True,
        samesite="none"
    )
    return {"status": "logged out"}


@app.get("/api/auth/verify")
async def verify(token: str = Depends(require_session)):
    return {"status": "valid"}


# ══════════════════════════════════════════════════════════════════════════════
#  REST ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/")
def root():
    return {"status": "ok", "message": "Trading Platform API is running"}


@app.get("/api/keepalive")
def keep_alive():
    """
    Keep-alive endpoint to prevent Hugging Face Space free tier sleep/shutdown.
    Configure a free cron-job (e.g., via cron-job.org) targeting this endpoint
    to run every 10 minutes between 9:10 AM and 3:40 PM IST, Monday to Friday.
    """
    from datetime import datetime, timezone, timedelta

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    market_open = sig_engine.is_nse_market_open()

    return {
        "status": "active",
        "message": "ApexTrade keep-alive handshake successful.",
        "current_time_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
        "market_status": "OPEN" if market_open else "CLOSED",
        "cron_setup_guide": {
            "target_url": "/api/keepalive",
            "schedule": "Every 10 minutes",
            "active_hours": "09:10 AM to 03:40 PM IST (03:40 to 10:10 UTC)",
            "active_days": "Monday to Friday",
            "purpose": "Keeps backend node warm during NSE trading session to eliminate 5m candle latency.",
        },
    }


@app.get("/api/quote")
def get_quote(symbol: str = Query(...)):
    result = sig_engine.get_symbol_quote(symbol)
    if not result:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result


@app.get("/api/upstox/authorize")
def upstox_authorize(state: Optional[str] = Query(None)):
    if not upstox_feed.UPSTOX_API_KEY or not upstox_feed.UPSTOX_REDIRECT_URI:
        raise HTTPException(
            status_code=400,
            detail="Upstox API key or Redirect URI not configured in the environment.",
        )

    import secrets

    csrf_token = secrets.token_urlsafe(32)
    original_state = state or ""
    oauth_state = f"{original_state}|{csrf_token}"

    url = upstox_feed.get_login_url(oauth_state)
    response = RedirectResponse(url)
    response.set_cookie(
        key="oauth_csrf_token",
        value=csrf_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )
    return response


@app.get("/api/upstox/callback")
def upstox_callback(
    request: Request, code: str = Query(...), state: Optional[str] = Query(None)
):
    # Validate CSRF token in state
    cookie_token = request.cookies.get("oauth_csrf_token")
    if not cookie_token:
        raise HTTPException(status_code=400, detail="Missing CSRF token in cookies")

    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    parts = state.rsplit("|", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid state parameter format")

    original_state, state_csrf_token = parts

    import hmac

    if not hmac.compare_digest(cookie_token, state_csrf_token):
        raise HTTPException(status_code=400, detail="CSRF token mismatch")

    # Reconstruct the exact redirect_uri used for this request to avoid OAuth mismatch
    redirect_uri = str(request.url).split("?")[0]
    if upstox_feed.UPSTOX_REDIRECT_URI.startswith(
        "https://"
    ) and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://")
    # Use the configured redirect URI directly to bypass proxy header issues
    redirect_uri = upstox_feed.UPSTOX_REDIRECT_URI

    res = upstox_feed.exchange_code_for_token(code, redirect_uri=redirect_uri)
    if not res:
        raise HTTPException(
            status_code=400,
            detail="Failed to exchange authorization code for access token",
        )

    redirect_target = original_state or ""
    if not redirect_target:
        redirect_uri_conf = upstox_feed.UPSTOX_REDIRECT_URI
        if "localhost" in redirect_uri_conf:
            redirect_target = "http://localhost:5173/account"
        else:
            redirect_target = "https://frontend-two-tau-82.vercel.app/account"
    else:
        if not redirect_target.endswith("/account"):
            if redirect_target.endswith("/"):
                redirect_target += "account"
            else:
                redirect_target += "/account"

    if "?" in redirect_target:
        redirect_target += "&broker_login=success"
    else:
        redirect_target += "?broker_login=success"

    response = RedirectResponse(redirect_target)
    response.delete_cookie("oauth_csrf_token")
    return response


@app.get("/auth/callback")
def upstox_callback_alias(
    request: Request, code: str = Query(...), state: Optional[str] = Query(None)
):
    return upstox_callback(request=request, code=code, state=state)


@app.get("/api/upstox/status")
def upstox_status():
    authorized = upstox_feed.is_authorized()
    status_data = {
        "authorized": authorized,
        "api_key_configured": bool(upstox_feed.UPSTOX_API_KEY),
        "redirect_uri_configured": bool(upstox_feed.UPSTOX_REDIRECT_URI),
    }
    if authorized:
        try:
            import db
            with db._conn() as c:
                row = c.execute("SELECT value FROM app_settings WHERE key='upstox_token'").fetchone()
                if row:
                    data = json.loads(row["value"])
                    status_data["updated_at"] = data.get("updated_at")
                    status_data["user_name"] = data.get("user_name")
        except Exception:
            pass
    return status_data


@app.get("/api/history")
def get_history(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    interval: str = Query(
        "1d", description="Bar interval: 1m,5m,15m,30m,1h,1d,1wk,1mo"
    ),
    range: str = Query("3mo", description="Date range: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max"),
):
    """
    Returns OHLCV candlestick bars ready for TradingView Lightweight Charts.

    Lightweight Charts expects:
      { time: 'YYYY-MM-DD' | unix_timestamp, open, high, low, close, volume }
    """
    VALID_INTERVALS = {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }
    VALID_RANGES = {
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    }

    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400, detail=f"Invalid interval. Choose from: {VALID_INTERVALS}"
        )
    if range not in VALID_RANGES:
        raise HTTPException(
            status_code=400, detail=f"Invalid range. Choose from: {VALID_RANGES}"
        )

    try:
        df = sig_engine.download_market_data_df(symbol, period=range, interval=interval)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No history for {symbol}")

        # Drop NaN values in OHLC columns to prevent JSON serialization crash
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No history data found for {symbol} after filtering NaNs",
            )

        # For intraday intervals, use Unix timestamps; for daily+, use date strings
        use_unix = interval not in {"1d", "5d", "1wk", "1mo", "3mo"}

        bars = []
        for ts, row in df.iterrows():
            if use_unix:
                t = int(ts.timestamp())
            else:
                t = ts.strftime("%Y-%m-%d")

            bars.append(
                {
                    "time": t,
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                }
            )

        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "range": range,
            "count": len(bars),
            "bars": bars,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/search")
def search_symbols(q: str = Query(..., min_length=1, description="Search query")):
    """
    Search symbols against the Upstox static instrument list.
    """
    symbol = q.upper().strip().replace(".NS", "")
    key = upstox_feed.get_instrument_key(symbol)
    if key:
        return {
            "results": [
                {
                    "symbol": symbol + ".NS",
                    "name": symbol,
                    "type": "NSE Equity",
                }
            ]
        }
    return {"results": []}


# ══════════════════════════════════════════════════════════════════════════════
#  NSE INTRADAY SIGNAL ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

_executor = ThreadPoolExecutor(max_workers=2)


@app.get("/api/signals")
@limiter.limit("15/minute")
@limiter.limit("5/10 seconds")
async def get_signals(
    request: Request,
    symbols: Optional[str] = Query(
        None,
        description="Comma-separated NSE symbols, e.g. RELIANCE.NS,TCS.NS. Omit for full scan.",
    ),
    limit: int = Query(20, ge=1, le=50, description="Max results to return"),
    _=Depends(require_session),
):
    """
    Scans NSE stocks and returns ranked intraday signals.
    Each signal includes: BUY/SELL/HOLD, confidence %, entry, target, stop-loss, R:R ratio, reasoning.
    """
    loop = asyncio.get_event_loop()

    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        # Map to watchlist entries or create minimal ones
        wl_map = {w["symbol"]: w for w in sig_engine.NSE_WATCHLIST}
        watchlist = [
            wl_map.get(s, {"symbol": s, "name": s.replace(".NS", ""), "sector": "NSE"})
            for s in sym_list
        ]
    else:
        watchlist = sig_engine.NSE_WATCHLIST

    # Run analysis concurrently in thread pool (scanning is blocking I/O)

    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                functools.partial(sig_engine.run_scan, watchlist),
            ),
            timeout=85
        )
    except asyncio.TimeoutError:
        return {
            "error": "Scan took too long (backend cold start)",
            "total": 0,
            "signals": [],
            "message": "First scan on free tier takes 2 min. Try again in 30s when backend is warm.",
        }

    return {
        "market": "NSE",
        "type": "intraday",
        "scan_time": datetime.utcnow().isoformat() + "Z",
        "total": len(results),
        "signals": results[:limit],
        "disclaimer": "Algorithmic signals only — not financial advice. Always apply your own judgement and risk management.",
    }


class ScanRequest(BaseModel):
    symbols: List[str]
    interval: str = "15m"
    capital: float = 100000.0
    trading_style: str = "Intraday Momentum"
    risk_level: str = "Medium"
    market_segment: str = "NSE"


@app.post("/api/scan")
@limiter.limit("15/minute")
@limiter.limit("5/10 seconds")
async def post_scan(
    req: ScanRequest,
    request: Request,
    _=Depends(require_session)
):
    """
    Scans a list of symbols and returns ranked intraday signals (POST alternative).
    """
    loop = asyncio.get_event_loop()
    
    # Map raw symbol strings to NSE_WATCHLIST structure
    wl_map = {w["symbol"]: w for w in sig_engine.NSE_WATCHLIST}
    watchlist = [wl_map.get(s.upper(), {"symbol": s.upper(), "name": s.upper().replace(".NS", ""), "sector": "NSE"}) for s in req.symbols]

    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                functools.partial(
                    sig_engine.run_scan,
                    watchlist,
                    req.interval,
                    req.trading_style,
                    req.risk_level,
                    req.market_segment,
                    req.capital
                )
            ),
            timeout=85
        )
    except asyncio.TimeoutError:
        return {
            "error": "Scan took too long (backend cold start)",
            "total": 0,
            "signals": [],
            "message": "First scan on free tier takes 2 min. Try again in 30s when backend is warm."
        }

    return {
        "market":      "NSE",
        "type":        "intraday",
        "scan_time":   datetime.utcnow().isoformat() + "Z",
        "total":       len(results),
        "signals":     results,
        "disclaimer":  "Algorithmic signals only — not financial advice. Always apply your own judgement and risk management.",
    }


@app.get("/api/signal/{symbol}")
async def get_signal_single(symbol: str, _=Depends(require_session)):
    """
    Full technical analysis for a single NSE symbol.
    Accepts symbol with or without .NS suffix.
    """
    sym = symbol.upper()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"

    wl_map = {w["symbol"]: w for w in sig_engine.NSE_WATCHLIST}
    meta = wl_map.get(
        sym, {"symbol": sym, "name": sym.replace(".NS", ""), "sector": "NSE"}
    )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        lambda: sig_engine.analyse_symbol(meta["symbol"], meta["name"], meta["sector"]),
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch data for {sym}. Market may be closed or symbol invalid.",
        )

    return result


class ChatMessage(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None  # { symbol, price, change_pct, ... }
    history: Optional[List[ChatMessage]] = None


@app.post("/api/chat")
@limiter.limit("30/minute")
@limiter.limit("10/10 seconds")
async def chat(req: ChatRequest, request: Request, _=Depends(require_session)):
    """
    AI trading assistant. Uses Gemini if GEMINI_API_KEY is set,
    otherwise falls back to a context-aware heuristic engine.
    """
    symbol = (req.context or {}).get("symbol", "the market")
    price = (req.context or {}).get("price", None)
    chg_pct = (req.context or {}).get("changePct", None)

    # ── Try Gemini (google-genai SDK) ────────────────────────────────────────
    if _genai_client:
        try:
            # Load custom trading knowledge base
            knowledge_content = ""
            knowledge_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "trading_knowledge.txt")
            )
            if os.path.exists(knowledge_path):
                try:
                    # Limit context size to allow the entire codebase blueprint and PDF manuals (up to 140000 chars)
                    with open(knowledge_path, "r", encoding="utf-8") as kf:
                        knowledge_content = kf.read(140000)
                except Exception:
                    pass

            # Fetch NewsAPI headlines for viewed symbol
            news_context = ""
            if symbol and symbol != "the market":
                try:
                    import news_feed

                    articles = news_feed.fetch_ticker_news(symbol)
                    if articles:
                        news_context = "--- LATEST NEWS CONTEXT ---\n"
                        for art in articles[:3]:  # Top 3 headlines
                            news_context += f"• {art.get('title')} (Published: {art.get('publishedAt')[:10]})\n"
                        news_context += "---------------------------\n\n"
                except Exception:
                    pass

            system_ctx = (
                f"You are an expert trading mentor and assistant embedded in the APEXTRADE platform. "
                f"You have been trained on the user's custom trading guides and PDFs (candlesticks, risk management, stop losses, etc.). "
                f"Use the following knowledge context to answer any trading query, explain strategies, and mentor the user: \n\n"
                f"--- KNOWLEDGE BASE EXTRACTS ---\n"
                f"{knowledge_content}\n"
                f"-------------------------------\n\n"
                f"{news_context}"
                f"Active Context: The user is currently viewing {symbol}"
                + (f" trading at ₹{price:.2f}" if price else "")
                + (f" ({chg_pct:+.2f}% today)" if chg_pct is not None else "")
                + ". \n\n"
                "IMPORTANT: The user may ask you about this active stock, or they may ask general questions about candlestick patterns, indicators, risk management, or other stocks. Answer any of these questions freely. Do not restrict your answers only to the active stock unless they ask about it. Provide concise, highly actionable advice. Never provide direct financial advice — always remind them this is educational. Keep responses under 180 words. Use **bold** sparingly for key terms."
            )

            # Construct chat thread including history
            formatted_history = ""
            if req.history:
                for h in req.history:
                    role_label = "User" if h.role == "user" else "Assistant"
                    formatted_history += f"{role_label}: {h.text}\n"

            prompt = (
                f"{system_ctx}\n\n{formatted_history}User: {req.message}\nAssistant:"
            )

            response = _genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return {"reply": response.text.strip(), "source": "gemini"}
        except Exception:
            pass  # fall through to heuristic

    # ── Heuristic fallback engine ─────────────────────────────────────────────
    msg_lower = req.message.lower()
    price_str = f"₹{price:,.2f}" if price else "current levels"
    chg_str = f"{chg_pct:+.2f}%" if chg_pct is not None else "unchanged"

    # ── Custom Knowledge Base Heuristic Matches ──────────────────────────────
    if "hammer" in msg_lower:
        reply = (
            "**Hammer Candlestick** — A bullish reversal candlestick pattern forming during a downtrend. "
            "It has a small body at the top of the price range and a long lower shadow (at least 2x the body length), "
            "representing strong price rejection at lows. A confirmation candle closing above the hammer's body validates the reversal setup. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif "doji" in msg_lower:
        reply = (
            "**Doji Candlestick** — A candlestick representing market equilibrium and indecision (virtually equal open and close). "
            "dragonfly Doji signals bullish rejection of lows, while Gravestone Doji signals bearish rejection of highs. Reversals "
            "require confirmation on the subsequent candle. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif "engulfing" in msg_lower:
        reply = (
            "**Engulfing Pattern** — A powerful two-candle reversal signal. A Bullish Engulfing pattern features a large green "
            "candle that completely wraps the previous red candle's body, indicating buyers have taken control. Bearish Engulfing is the opposite. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif any(w in msg_lower for w in ["candlestick", "candle", "pattern"]):
        reply = (
            "**Candlestick Patterns** — Visual maps of price history. Key structures like Hammers, Dojis, and Engulfing lines "
            "signal potential trend reversals. Seek confluence with major support/resistance levels and check volume expansion for validation. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif "rsi" in msg_lower:
        reply = (
            "**RSI (Relative Strength Index)** — A momentum oscillator measuring the speed and change of price moves from 0 to 100. "
            "Traditionally, values above 70 indicate overbought conditions (pullback warning) and values below 30 indicate oversold setups. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif "macd" in msg_lower:
        reply = (
            "**MACD (Moving Average Convergence Divergence)** — A trend-following momentum indicator. Crossover of the MACD line "
            "above the signal line suggests bullish momentum; crossover below warns of bearish acceleration. Divergence from price indicates reversals. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif any(w in msg_lower for w in ["ema", "sma", "moving average"]):
        reply = (
            "**Moving Averages** — Trend following tools. Simple Moving Average (SMA) tracks equal weights, while Exponential Moving Average (EMA) "
            "prioritizes recent prices for faster responses. Watch for crossover triggers (e.g. 9 EMA crossing 21 EMA) to confirm trend shifts. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif any(
        w in msg_lower
        for w in ["stop", "sl", "risk", "size", "sizing", "capital", "money"]
    ):
        reply = (
            "**Risk Management Policy** — Limit risk to 1-2% of total capital per trade. Calculate your position size dynamically: "
            "Position Size = (Capital * Risk %) / (Entry Price - Stop Loss Price). Place stop losses below recent swing lows or moving average lines. "
            "*(Local fallback response - set GEMINI_API_KEY for full AI mentoring)*"
        )
    elif any(w in msg_lower for w in ["buy", "long", "bullish", "upside"]):
        reply = (
            f"**{symbol} Bull Case** — At {price_str} ({chg_str} today), "
            f"consider accumulating on dips to key support. Watch for volume "
            f"confirmation on any breakout above recent highs. Set a stop-loss "
            f"below the most recent swing low. Risk/reward matters more than direction."
        )
    elif any(w in msg_lower for w in ["sell", "short", "bearish", "downside"]):
        reply = (
            f"**{symbol} Bear Case** — Trading at {price_str}, if price breaks below "
            f"key support with elevated volume, the path of least resistance may be lower. "
            f"Watch RSI for oversold conditions before shorting. Always use a defined risk limit."
        )
    elif any(w in msg_lower for w in ["price", "worth", "value", "target"]):
        reply = (
            f"**{symbol}** is currently at {price_str} ({chg_str} today). "
            f"For price targets, analysts typically use DCF models, P/E multiples, "
            f"or technical levels. Check consensus estimates on earnings platforms. "
            f"Past performance doesn't guarantee future results."
        )
    elif any(w in msg_lower for w in ["trend", "momentum", "rsi", "macd", "technical"]):
        reply = (
            f"**{symbol} Technical Picture** — At {price_str}, key signals to watch: "
            f"50/200-day moving average alignment, RSI (overbought >70, oversold <30), "
            f"MACD crossovers, and Bollinger Band width for volatility. "
            f"Volume on each price move is your confirmation signal."
        )
    elif any(w in msg_lower for w in ["news", "catalyst", "earnings", "event"]):
        reply = (
            f"**{symbol} Catalysts** — Key events to track: earnings dates, "
            f"Fed announcements, sector rotation flows, and institutional filings (13F). "
            f"I'm the rule-based fallback — set GEMINI_API_KEY for real-time AI analysis."
        )
    elif any(w in msg_lower for w in ["risk", "stop", "position", "size"]):
        reply = (
            f"**Risk Management for {symbol}** — Never risk more than 1-2% of your "
            f"portfolio on a single trade. With {symbol} at {price_str}, calculate your "
            f"position size based on your stop-loss distance: (Portfolio * 0.01) / (Entry - Stop). "
            f"Paper trading mode is active — no real orders are placed."
        )
    else:
        reply = (
            f"**{symbol}** @ {price_str} ({chg_str}) — I'm your AI trading assistant. "
            f"Ask me about price targets, technical signals, risk management, or market catalysts. "
            f"💡 Tip: Set the `GEMINI_API_KEY` environment variable to unlock real Gemini AI responses."
        )

    return {"reply": reply, "source": "heuristic"}


def is_nse_market_open() -> bool:
    """
    NSE market is open Monday-Friday, 9:15 AM to 3:30 PM IST.
    IST is UTC + 5:30.
    """
    from datetime import datetime, timedelta, timezone

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    if now_ist.weekday() >= 5:
        return False

    minutes_since_midnight = now_ist.hour * 60 + now_ist.minute
    start_minutes = 9 * 60 + 15
    end_minutes = 15 * 60 + 30

    return start_minutes <= minutes_since_midnight <= end_minutes


# Fallback seed prices for Indian stocks if provider feed fails
SEED_PRICES = {
    "HAL.NS": 4550.0,
    "BEL.NS": 295.0,
    "RVNL.NS": 385.0,
    "IREDA.NS": 185.0,
    "HUDCO.NS": 275.0,
    "COALINDIA.NS": 485.0,
    "NHPC.NS": 95.0,
    "ADANIPORTS.NS": 1405.0,
    "TATAPOWER.NS": 445.0,
    "BHEL.NS": 305.0,
}

# Live prices cache seeded initially with baseline seed prices
LIVE_PRICES_CACHE = {
    sym: {"price": price, "prev_close": price, "timestamp": int(time.time() * 1000)}
    for sym, price in SEED_PRICES.items()
}

_crawl_executor = ThreadPoolExecutor(max_workers=5)

# Track last HTTP request time to keep crawler active during HTTP polling fallback
last_prices_request_time = 0.0


async def fetch_live_quotes_loop():
    """
    Background crawler task that runs every 10 seconds to fetch the latest
    quotes for all watchlisted NSE stocks and updates LIVE_PRICES_CACHE.
    """
    import functools

    watchlist_symbols = [w["symbol"] for w in sig_engine.NSE_WATCHLIST]

    while True:
        # Preserve API rate limits / credits when no active users are online
        # and no recent HTTP polling requests have been received
        now = time.time()
        if len(active_connections) == 0 and (now - last_prices_request_time > 30.0):
            await asyncio.sleep(5)
            continue

        sleep_time = 10
        try:
            loop = asyncio.get_event_loop()

            if upstox_feed.is_authorized():
                # Fetch live quotes from Upstox
                quotes = await loop.run_in_executor(
                    _crawl_executor,
                    functools.partial(upstox_feed.get_live_quotes, watchlist_symbols),
                )
                if quotes:
                    for sym in watchlist_symbols:
                        quote = quotes.get(sym)
                        if quote:
                            data = {
                                "price": quote["price"],
                                "prev_close": quote["prev_close"],
                                "timestamp": int(time.time() * 1000),
                            }
                            LIVE_PRICES_CACHE[sym] = data
                            # Also cache clean key for easier frontend lookup
                            clean_sym = sym.replace(".NS", "").replace(".BO", "")
                            LIVE_PRICES_CACHE[clean_sym] = data
                # Sleep for 2 seconds when Upstox is active to fetch ticks
                sleep_time = 2
            else:
                print("[live quotes] Upstox not authorized — no live prices")
                sleep_time = 10
        except Exception as e:
            print(f"[fetch_live_quotes_loop] Error: {e}")

        # Reconcile pending signals after prices update
        try:
            reconcile_pending_signals()
        except Exception:
            pass

        await asyncio.sleep(sleep_time)


def reconcile_pending_signals():
    """
    Checks all PENDING signals in the database against the latest prices in LIVE_PRICES_CACHE.
    Marks targets/stops as hit, and expires old intraday trades.
    """
    pending = db.get_pending_signals()
    if not pending:
        return

    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    
    signal_updates = []

    for sig in pending:
        symbol = sig["symbol"]
        cached = LIVE_PRICES_CACHE.get(symbol)
        if not cached:
            continue

        current_price = cached["price"]
        entry_price = sig["entry_price"]
        target = sig["target"]
        stop_loss = sig["stop_loss"]
        signal_type = sig["signal_type"]
        scan_type = sig["scan_type"]
        scanned_at_str = sig["scanned_at"]

        hit = False
        status = "PENDING"
        exit_price = current_price
        pnl = 0.0

        if "BUY" in signal_type:
            if current_price >= target:
                hit = True
                status = "HIT_TARGET"
                exit_price = target
                pnl = (exit_price - entry_price) / entry_price * 100
            elif current_price <= stop_loss:
                hit = True
                status = "HIT_STOP"
                exit_price = stop_loss
                pnl = (exit_price - entry_price) / entry_price * 100
        elif "SELL" in signal_type:
            if current_price <= target:
                hit = True
                status = "HIT_TARGET"
                exit_price = target
                pnl = (entry_price - exit_price) / entry_price * 100
            elif current_price >= stop_loss:
                hit = True
                status = "HIT_STOP"
                exit_price = stop_loss
                pnl = (entry_price - exit_price) / entry_price * 100

        if hit:
            signal_updates.append((status, exit_price, db._now_ist(), pnl, sig["id"]))
            continue

        # Check Expiry
        try:
            clean_ts = scanned_at_str.replace("Z", "")
            if "+" in clean_ts:
                clean_ts = clean_ts.split("+")[0]
            scanned_dt_utc = datetime.fromisoformat(clean_ts)
            scanned_dt_ist = scanned_dt_utc + timedelta(hours=5, minutes=30)

            if scan_type == "INTRADAY":
                is_future_day = now_ist.date() > scanned_dt_ist.date()
                is_past_market_close = now_ist.hour > 15 or (
                    now_ist.hour == 15 and now_ist.minute >= 30
                )

                if is_future_day or (
                    now_ist.date() == scanned_dt_ist.date() and is_past_market_close
                ):
                    pnl_calc = 0.0
                    if "BUY" in signal_type:
                        pnl_calc = (current_price - entry_price) / entry_price * 100
                    else:
                        pnl_calc = (entry_price - current_price) / entry_price * 100
                        
                    signal_updates.append(("EXPIRED", current_price, db._now_ist(), pnl_calc, sig["id"]))
            else:
                # OVERNIGHT: 5 days limit
                days_diff = (now_utc - scanned_dt_utc).days
                if days_diff >= 5:
                    pnl_calc = 0.0
                    if "BUY" in signal_type:
                        pnl_calc = (current_price - entry_price) / entry_price * 100
                    else:
                        pnl_calc = (entry_price - current_price) / entry_price * 100
                        
                    signal_updates.append(("EXPIRED", current_price, db._now_ist(), pnl_calc, sig["id"]))
        except Exception:
            pass

    if signal_updates:
        db.update_signals_batch(signal_updates)


AUTO_SCAN_INTERVAL_OPEN = 60
AUTO_SCAN_INTERVAL_CLOSED = 3600


async def cleanup_sessions_loop():
    """
    Background task to clean up expired sessions periodically.
    Runs every 1 hour (3600 seconds) to prevent memory leak
    from unbounded ACTIVE_SESSIONS dictionary.
    """
    from auth_helpers import cleanup_sessions
    while True:
        try:
            cleanup_sessions()
        except Exception as e:
            print(f"[cleanup_sessions_loop] error: {e}")
        await asyncio.sleep(3600)


async def prediction_resolver_worker():
    """
    Batched resolution engine that bypasses LIVE_PRICES_CACHE.
    Fetches unique symbols directly from API to prevent DDoS.
    """
    loop = asyncio.get_event_loop()
    while True:
        try:
            predictions = db.get_predictions()
            pending = [p for p in predictions if p.get("status") == "PENDING"]
            
            # Phase Omega: Filter Attribution Engine (resolve rejected signals)
            rejected_pending = db.get_pending_rejected_signals()
            
            symbols = list(set([p["symbol"] for p in pending] + [r["symbol"] for r in rejected_pending]))
            
            if symbols:
                # Fetch quotes synchronously in thread pool
                quotes = await loop.run_in_executor(
                    _executor,
                    functools.partial(upstox_feed.get_live_quotes, symbols)
                )
                
                if quotes:
                    for pred in pending:
                        symbol = pred["symbol"]
                        live = quotes.get(symbol)
                        if not live:
                            continue
                            
                        price = live["price"]
                        is_bullish = pred["prediction_type"].upper() == "BULLISH"
                        target = pred["target_price"]
                        stop = pred["stop_loss"]
                        entry = pred["entry_price"]
                        
                        hit_target = (is_bullish and price >= target) or (not is_bullish and price <= target)
                        hit_stop = (is_bullish and price <= stop) or (not is_bullish and price >= stop)
                        
                        pred_date_str = pred["prediction_date"]
                        expired = False
                        holding_time_minutes = 0.0
                        try:
                            from dateutil import parser
                            pred_time = parser.parse(pred_date_str)
                            if pred_time.tzinfo is None:
                                ist_tz = timezone(timedelta(hours=5, minutes=30))
                                pred_time = pred_time.replace(tzinfo=ist_tz)
                            now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
                            delta = now_ist - pred_time
                            holding_time_minutes = delta.total_seconds() / 60.0
                            if delta > timedelta(hours=24):
                                expired = True
                        except Exception:
                            pass
                            
                        if hit_target or hit_stop or expired:
                            resolution_reason = "EXPIRED"
                            if hit_target:
                                resolution_reason = "TARGET_HIT"
                                status = "WIN"
                            elif hit_stop:
                                resolution_reason = "STOP_HIT"
                                status = "LOSS"
                            else:
                                status = "TIMEOUT"
                                
                            # Calculate PnL
                            pnl_pct = 0.0
                            if entry > 0:
                                if is_bullish:
                                    pnl_pct = ((price - entry) / entry) * 100
                                else:
                                    pnl_pct = ((entry - price) / entry) * 100
                                    
                            pnl_pct = round(pnl_pct, 2)
                            risk_amount = pred.get("risk_amount") or 0.0
                            pnl_inr = 0.0
                            r_multiple = 0.0
                            
                            if risk_amount > 0:
                                qty = risk_amount / abs(entry - stop) if abs(entry - stop) > 0 else 0
                                pnl_inr = round(qty * abs(price - entry) * (1 if pnl_pct >= 0 else -1), 2)
                                r_multiple = round(pnl_inr / risk_amount, 2)
                                
                            # Slippage Calculation: difference between target/stop and actual fill price
                            slippage_pct = 0.0
                            if hit_target and target > 0:
                                slippage_pct = abs(price - target) / target * 100.0
                            elif hit_stop and stop > 0:
                                slippage_pct = abs(price - stop) / stop * 100.0
                                
                            db.resolve_prediction(
                                pred_id=pred["id"], 
                                actual_outcome=price, 
                                status=status,
                                exit_price=price,
                                holding_time_minutes=round(holding_time_minutes, 1),
                                pnl_pct=pnl_pct,
                                pnl_inr=pnl_inr,
                                r_multiple=r_multiple,
                                resolution_reason=resolution_reason,
                                fill_time=now_ist.isoformat(),
                                slippage_pct=round(slippage_pct, 4)
                            )
                            
                            # Update Equity Curve sequentially
                            if pnl_inr != 0:
                                eq_after, peak = db.get_latest_equity()
                                new_eq = eq_after + pnl_inr
                                new_peak = max(peak, new_eq)
                                drawdown = round(((new_peak - new_eq) / new_peak) * 100, 2) if new_peak > 0 else 0.0
                                db.add_equity_curve(pred["id"], eq_after, new_eq, new_peak, drawdown)
                                
        except Exception as e:
            print(f"[prediction_resolver_worker] error: {e}")
            
        await asyncio.sleep(60)


async def metrics_worker():
    """
    Asynchronously aggregates analytics and populates the metrics_cache.
    Ensures dashboard loads instantly without recomputing all historical trades.
    """
    while True:
        try:
            predictions = db.get_predictions()
            resolved = [p for p in predictions if p.get("status") in ["WIN", "LOSS", "TIMEOUT", "CORRECT", "INCORRECT"]]
            
            total_wins = sum(1 for p in resolved if p.get("pnl_inr", 0) > 0 or p["status"] in ["WIN", "CORRECT"])
            total_losses = sum(1 for p in resolved if p.get("pnl_inr", 0) < 0 or p["status"] in ["LOSS", "INCORRECT"])
            
            winning_pnl = sum(p.get("pnl_inr", 0) for p in resolved if p.get("pnl_inr", 0) > 0)
            losing_pnl = abs(sum(p.get("pnl_inr", 0) for p in resolved if p.get("pnl_inr", 0) < 0))
            
            profit_factor = round(winning_pnl / losing_pnl, 2) if losing_pnl > 0 else (999.0 if winning_pnl > 0 else 0)
            
            win_rate = (total_wins / len(resolved) * 100) if resolved else 0.0
            loss_rate = (total_losses / len(resolved) * 100) if resolved else 0.0
            
            avg_win_pct = sum(p.get("pnl_pct", 0) for p in resolved if p.get("pnl_pct", 0) > 0) / total_wins if total_wins else 0
            avg_loss_pct = sum(p.get("pnl_pct", 0) for p in resolved if p.get("pnl_pct", 0) < 0) / total_losses if total_losses else 0
            
            ev_pct = round((win_rate/100 * avg_win_pct) - (loss_rate/100 * abs(avg_loss_pct)), 2)
            avg_r = round(sum(p.get("r_multiple", 0) for p in resolved) / len(resolved), 2) if resolved else 0.0
            
            holding_times = [p.get("holding_time_minutes", 0) for p in resolved if p.get("holding_time_minutes")]
            avg_holding = round(sum(holding_times) / len(holding_times), 1) if holding_times else 0.0
            
            fastest_win = min([p.get("holding_time_minutes", 0) for p in resolved if p.get("pnl_inr", 0) > 0 and p.get("holding_time_minutes")], default=0)
            longest_win = max([p.get("holding_time_minutes", 0) for p in resolved if p.get("pnl_inr", 0) > 0 and p.get("holding_time_minutes")], default=0)
            longest_loss = max([p.get("holding_time_minutes", 0) for p in resolved if p.get("pnl_inr", 0) < 0 and p.get("holding_time_minutes")], default=0)
            
            _, peak = db.get_latest_equity()
            eq_after, _ = db.get_latest_equity()
            max_drawdown = round(((peak - eq_after) / peak) * 100, 2) if peak > 0 else 0.0
            
            setups = {}
            for p in resolved:
                stype = p.get("setup_type", "UNKNOWN")
                if stype not in setups:
                    setups[stype] = {"trades": 0, "wins": 0, "winning_pnl": 0, "losing_pnl": 0, "r_sum": 0}
                setups[stype]["trades"] += 1
                if p.get("pnl_inr", 0) > 0:
                    setups[stype]["wins"] += 1
                    setups[stype]["winning_pnl"] += p.get("pnl_inr", 0)
                else:
                    setups[stype]["losing_pnl"] += abs(p.get("pnl_inr", 0))
                setups[stype]["r_sum"] += p.get("r_multiple", 0)
                
            leaderboard = []
            for stype, sdata in setups.items():
                trades = sdata["trades"]
                wr = round((sdata["wins"] / trades) * 100, 1) if trades else 0
                pf = round(sdata["winning_pnl"] / sdata["losing_pnl"], 2) if sdata["losing_pnl"] > 0 else (99.0 if sdata["winning_pnl"] > 0 else 0)
                avg_r_setup = round(sdata["r_sum"] / trades, 2) if trades else 0
                leaderboard.append({
                    "setup": stype,
                    "trades": trades,
                    "win_rate": wr,
                    "profit_factor": pf,
                    "avg_r": avg_r_setup
                })
            leaderboard.sort(key=lambda x: x["avg_r"], reverse=True)
            
            cache_data = {
                "total_resolved": len(resolved),
                "profit_factor": profit_factor,
                "ev_pct": ev_pct,
                "avg_r": avg_r,
                "avg_holding": avg_holding,
                "fastest_win": fastest_win,
                "longest_win": longest_win,
                "longest_loss": longest_loss,
                "max_drawdown": max_drawdown,
                "leaderboard": leaderboard
            }
            db.set_metrics_cache("dashboard_metrics", cache_data)
        except Exception as e:
            print(f"[metrics_worker] error: {e}")
            import traceback
            traceback.print_exc()
            
        await asyncio.sleep(60)


async def signal_scanner_worker():
    """
    Background task:
      - Market OPEN  → scan every 60 s, log signals to DB
      - Market CLOSED → scan every 60 min for overnight signals
    """
    loop = asyncio.get_event_loop()
    while True:
        try:
            market_open = is_nse_market_open()
            scan_type = "INTRADAY" if market_open else "OVERNIGHT"

            # Phase Omega: Dual Kill Switch Check
            risk_settings = db.get_risk_settings()
            portfolio = db.get_portfolio_state()
            
            # Simple daily drawdown check
            current_eq = portfolio.get("current_equity", 100000.0)
            daily_start = portfolio.get("daily_equity", 100000.0)
            peak_eq = portfolio.get("peak_equity", 100000.0)
            
            daily_loss_pct = ((current_eq - daily_start) / daily_start) * 100
            peak_dd_pct = ((current_eq - peak_eq) / peak_eq) * 100
            
            if daily_loss_pct <= risk_settings["daily_loss_limit"] or peak_dd_pct <= risk_settings["daily_drawdown_limit"]:
                print(f"[signal_scanner_worker] KILL SWITCH ACTIVE. Daily Loss: {daily_loss_pct:.2f}%, Peak DD: {peak_dd_pct:.2f}%")
                await asyncio.sleep(60 * 5) # Sleep 5 minutes and retry (maybe admin reset it)
                continue

            # ── 1. Run signal scan ───────────────────────────────────────────
            results = await loop.run_in_executor(
                _executor,
                functools.partial(sig_engine.run_scan, sig_engine.NSE_WATCHLIST),
            )

            sentiment_pct = 50
            nifty_trend_bias = "CONSOLIDATION"
            if results:
                nifty_trend_bias = results[0].get("nifty_trend", "CONSOLIDATION")
                buys_count = sum(1 for s in results if s.get("score", 0) > 0)
                sentiment_pct = int(buys_count / len(results) * 100) if results else 50

            valid_signals = []
            for sig in results:
                if sig.get("signal") in ("BUY", "SELL") and sig.get("confidence", 0) >= 60:
                    sig["direction"]  = sig["signal"]
                    sig["entry"]      = sig.get("price", sig.get("entry", 0))
                    sig["scan_type"]  = scan_type
                    valid_signals.append(sig)

            if valid_signals:
                db.add_signals_batch(valid_signals)
                for sig in valid_signals:
                    try:
                        vwap_dist = ((sig["price"] - sig["vwap"]) / sig["vwap"] * 100) if sig.get("vwap") else 0.0
                        pred_data = {
                            "symbol": sig["symbol"],
                            "prediction_type": "BULLISH" if sig["signal"] == "BUY" else "BEARISH",
                            "entry_price": sig["entry"],
                            "target_price": sig["target"],
                            "stop_loss": sig["stop_loss"],
                            "confidence_score": sig["confidence"],
                            "rsi": sig.get("rsi"),
                            "macd": sig.get("macd_hist"),
                            "adx": sig.get("adx"),
                            "sector": sig.get("sector"),
                            "market_cap": sig.get("market_cap"),
                            "volume_ratio": sig.get("vol_ratio"),
                            "vwap_distance": vwap_dist,
                            "atr": sig.get("atr"),
                            "news_score": sig.get("news_sentiment", 0.0),
                            "market_breadth": float(sentiment_pct),
                            "sector_strength": float(sig.get("sector_score", 10.0)),
                            "nifty_trend": nifty_trend_bias,
                            "status": "PENDING",
                            "reason": sig.get("reasoning", ""),
                            "setup_type": sig.get("setup_type", "SYSTEM_EDGE"),
                            "market_regime_snapshot": sig.get("market_regime", "UNKNOWN"),
                            "risk_amount": sig.get("risk_amount", 0.0),
                            "confidence_probability": sig.get("confidence_probability", 0.0),
                            "regime_score": sig.get("regime_score", 0.0),
                            "sector_score": sig.get("sector_score", 0.0),
                            "volume_score": sig.get("volume_score", 0.0),
                            "rs_score": sig.get("rs_score", 0.0),
                            "trade_quality_score": sig.get("trade_quality_score", 0.0),
                            "correlation_score": sig.get("correlation_score", 0.0)
                        }
                        db.add_prediction(pred_data)
                    except Exception as pe:
                        print(f"[signal_scanner_worker] Failed to log prediction: {pe}")

            # ── 2. Reconcile signals_history vs live prices ──────────────────
            pending = db.get_pending_signals()
            signal_updates = []
            for trade in pending:
                live = LIVE_PRICES_CACHE.get(trade["symbol"])
                if live is None:
                    continue
                price = live["price"]
                is_buy = "BUY" in trade["signal_type"]
                hit_target = (is_buy and price >= trade["target"]) or (not is_buy and price <= trade["target"])
                hit_stop = (is_buy and price <= trade["stop_loss"]) or (not is_buy and price >= trade["stop_loss"])
                if hit_target:
                    pnl = db._calc_pnl(trade["signal_type"], trade["entry_price"], price)
                    signal_updates.append(("HIT_TARGET", price, db._now_ist(), pnl, trade["id"]))
                elif hit_stop:
                    pnl = db._calc_pnl(trade["signal_type"], trade["entry_price"], price)
                    signal_updates.append(("HIT_STOP", price, db._now_ist(), pnl, trade["id"]))

            if signal_updates:
                db.update_signals_batch(signal_updates)

            # ── 3. Expire stale intraday signals ─────────────────────────────
            db.expire_old_intraday()

        except Exception as e:
            print(f"[signal_scanner_worker] error: {e}")

        sleep_dur = AUTO_SCAN_INTERVAL_OPEN if is_nse_market_open() else AUTO_SCAN_INTERVAL_CLOSED
        await asyncio.sleep(sleep_dur)


@app.on_event("startup")
async def startup_event():
    db.init_db()
    
    # Import governance worker
    import governance_worker
    
    asyncio.create_task(fetch_live_quotes_loop())
    asyncio.create_task(signal_scanner_worker())
    asyncio.create_task(prediction_resolver_worker())
    asyncio.create_task(metrics_worker())
    asyncio.create_task(cleanup_sessions_loop())
    asyncio.create_task(governance_worker.governance_loop())


@app.get("/api/prices")
@limiter.limit("30/minute")
async def get_live_prices(request: Request, _=Depends(require_session)):
    """
    HTTP fallback for live prices when WebSocket is unavailable.
    Returns the full LIVE_PRICES_CACHE dictionary.
    """
    global last_prices_request_time
    last_prices_request_time = time.time()
    return {
        "type": "tick",
        "data": [
            {
                "symbol": sym,
                "price": info["price"],
                "prev_close": info.get("prev_close", info["price"]),
                "timestamp": info.get("timestamp", int(time.time() * 1000)),
            }
            for sym, info in LIVE_PRICES_CACHE.items()
            if "." in sym  # Only return full symbol keys like HAL.NS, not clean keys
        ],
        "market_status": "OPEN" if is_nse_market_open() else "CLOSED",
    }

@app.websocket("/ws/prices")
async def websocket_prices(
    websocket: WebSocket,
    symbols: str = "HAL.NS,BEL.NS,RVNL.NS,IREDA.NS,HUDCO.NS,COALINDIA.NS,NHPC.NS,ADANIPORTS.NS,TATAPOWER.NS,BHEL.NS",
):
    await websocket.accept()

    # Validate session token via cookie
    token = websocket.cookies.get("apt_token")
    if token and token.startswith("apt_"):
        if token not in ACTIVE_SESSIONS:
            import logging
            logging.warning(
                "[WS] Token not found in active sessions (may be stale after restart)"
            )
    elif not token:
        import logging
        logging.warning("[WS] No token provided via cookie — anonymous WebSocket connection")
        # You could also close the connection here if auth is strict:
        # await websocket.close(code=4001)
        # return

    active_connections.append(websocket)

    watch = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    # Store local tracking price states to simulate smooth tick transitions
    local_prices: dict[str, float] = {}
    local_prev_closes: dict[str, float] = {}

    for sym in watch:
        cached = LIVE_PRICES_CACHE.get(
            sym,
            {
                "price": SEED_PRICES.get(sym, 150.0),
                "prev_close": SEED_PRICES.get(sym, 150.0),
            },
        )
        local_prices[sym] = cached["price"]
        local_prev_closes[sym] = cached["prev_close"]

    try:
        while True:
            # Check for incoming control messages (non-blocking)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                msg = json.loads(raw)
                if msg.get("action") == "subscribe" and "symbols" in msg:
                    new_syms = [s.strip().upper() for s in msg["symbols"] if s.strip()]
                    for sym in new_syms:
                        if sym not in local_prices:
                            cached = LIVE_PRICES_CACHE.get(
                                sym,
                                {
                                    "price": SEED_PRICES.get(sym, 150.0),
                                    "prev_close": SEED_PRICES.get(sym, 150.0),
                                },
                            )
                            local_prices[sym] = cached["price"]
                            local_prev_closes[sym] = cached["prev_close"]
                    watch = new_syms
            except asyncio.TimeoutError:
                pass

            market_open = is_nse_market_open()
            use_upstox = upstox_feed.is_authorized()
            ticks = []
            for sym in watch:
                cached = LIVE_PRICES_CACHE.get(sym)
                if cached:
                    baseline_price = cached["price"]
                    local_prev_closes[sym] = cached["prev_close"]
                else:
                    baseline_price = local_prices.get(sym, SEED_PRICES.get(sym, 150.0))

                if market_open and not use_upstox:
                    # Stream simulated tick fluctuations around the live baseline price (fallback only)
                    price = _simulate_tick(baseline_price)
                    local_prices[sym] = price
                else:
                    # Gating: Closed market or Upstox authorized (use true live tick prices)
                    price = baseline_price
                    local_prices[sym] = price

                ticks.append(
                    {
                        "symbol": sym,
                        "price": round(price, 4),
                        "prev_close": round(local_prev_closes.get(sym, price), 4),
                        "timestamp": int(time.time() * 1000),
                    }
                )

            await websocket.send_json(
                {
                    "type": "tick",
                    "data": ticks,
                    "market_status": "OPEN" if market_open else "CLOSED",
                }
            )
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


def _simulate_tick(last_price: float) -> float:
    """
    Micro random-walk tick. Replace the body of this function with a real
    feed (Alpaca stream, Polygon WebSocket, etc.) and this endpoint needs
    zero other changes.
    """
    change_pct = random.gauss(0, 0.0008)  # ~0.08% std dev per tick
    return max(0.01, last_price * (1 + change_pct))


# Backtest endpoints are now served via backtest_routes.py (app.include_router)


# ══════════════════════════════════════════════════════════════════════════════
#  CAPITAL ALLOCATION ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════


class CapitalRequest(BaseModel):
    capital: float
    interval: str = "5m"
    risk_level: str = "Medium"
    market_segment: str = "NSE"
    trading_style: str = "Intraday Momentum"
    max_recommendations: int = 5


@app.post("/api/allocate")
@limiter.limit("3/minute")
async def allocate_capital(
    req: CapitalRequest, request: Request, _=Depends(require_session)
):
    """
    Scan HIGH_VOLATILITY_UNIVERSE matched to capital size.
    Small capital → cheap volatile stocks (YESBANK, SUZLON, RVNL…)
    Large capital → full universe including mid/large caps.
    """
    if req.capital < 500:
        raise HTTPException(status_code=400, detail="Minimum capital is ₹500")


    loop = asyncio.get_event_loop()

    # Pick the right universe based on capital size
    target_symbols = capital_allocator.get_target_universe(req.capital)

    # Convert symbol strings to the dict format sig_engine.run_scan expects
    # (run_scan accepts both plain symbol strings and dicts with 'symbol' key)
    try:
        signals = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                functools.partial(
                    sig_engine.run_scan,
                    target_symbols,
                    req.interval,
                    req.trading_style,
                    req.risk_level,
                    req.market_segment,
                    req.capital,
                )
            ),
            timeout=150
        )
    except asyncio.TimeoutError:
        return {
            "error": "Scan took too long (backend cold start)",
            "positions": [],
            "message": "First scan on free tier takes 2 min. Try again in 30s when backend is warm.",
        }

    # Normalise signal fields so allocator can read them
    normalised = []
    for s in signals:
        normalised.append(
            {
                **s,
                "direction": s.get("signal", s.get("direction", "")),
                "entry": s.get("price", s.get("entry", s.get("entry_price", 0))),
                "entry_price": s.get("price", s.get("entry", s.get("entry_price", 0))),
            }
        )

    plan = capital_allocator.allocate(
        req.capital,
        normalised,
        style=req.trading_style,
        risk=req.risk_level,
        max_recommendations=req.max_recommendations,
    )
    plan["all_signals"] = normalised

    # Log generated recommendations in predictions_history database
    for pos in plan.get("positions", []):
        try:
            pred_data = {
                "symbol": pos["symbol"],
                "prediction_type": "UP",  # all allocator signals are BUY opportunities
                "entry_price": pos["entry_price"],
                "target_price": pos["target1"],
                "stop_loss": pos["stop_loss"],
                "confidence_score": pos["confidence"],
                "rsi": pos.get("rsi"),
                "macd": pos.get("macd_hist"),
                "adx": pos.get("adx"),
                "status": "PENDING",
                "reason": ", ".join(pos.get("reasons", [])),
            }
            db.add_prediction(pred_data)
        except Exception as e:
            print(
                f"[api/allocate] Error archiving recommendation for {pos['symbol']}: {e}"
            )

    return plan


@app.post("/api/allocate/quick")
@limiter.limit("3/minute")
async def allocate_capital_quick(
    req: CapitalRequest, request: Request, _=Depends(require_session)
):
    """
    Fast allocation using already-cached live prices (no fresh yfinance scan).
    Returns instantly if LIVE_PRICES_CACHE is warm; falls back to full scan otherwise.
    """
    if req.capital < 500:
        raise HTTPException(status_code=400, detail="Minimum capital is ₹500")

    # Build lightweight signals from the live price cache
    quick_signals = []
    for entry in sig_engine.NSE_WATCHLIST:
        sym = entry["symbol"]

        # Apply segment filter
        if req.market_segment == "BSE" and not sym.endswith(".BO"):
            continue
        elif req.market_segment == "F&O" and sym not in [
            "HAL.NS",
            "BEL.NS",
            "RVNL.NS",
            "COALINDIA.NS",
            "ADANIPORTS.NS",
            "TATAPOWER.NS",
            "BHEL.NS",
        ]:
            continue

        cached = LIVE_PRICES_CACHE.get(sym)
        if not cached:
            continue
        price = cached["price"]
        quick_signals.append(
            {
                "symbol": sym,
                "name": entry["name"],
                "sector": entry["sector"],
                "direction": "BUY",  # optimistic placeholder
                "entry": price,
                "entry_price": price,
                "target": round(price * 1.025, 2),
                "target1": round(price * 1.025, 2),
                "target2": round(price * 1.045, 2),
                "stop_loss": round(price * 0.985, 2),
                "confidence": 60,
                "atr": round(price * 0.012, 2),
                "rr_ratio": 1.67,
                "rsi": 50,
                "macd_hist": 0.0,
                "adx": 20,
                "reasons": ["Cached Live Price Signal"],
                "sector_strength": "Medium",
                "expected_move_pct": 2.5,
            }
        )

    if not quick_signals:
        # Cache not warm yet — fall back to full scan
        return await allocate_capital(req)

    plan = capital_allocator.allocate(
        req.capital,
        quick_signals,
        style=req.trading_style,
        risk=req.risk_level,
        max_recommendations=req.max_recommendations,
    )
    plan["all_signals"] = quick_signals
    plan["note"] = (
        "Quick allocation using cached prices — run /api/allocate for a full fresh scan."
    )

    return plan



# ── Trade Journal API ────────────────────────────────────────────────────────


class JournalEntryCreate(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    exit_price: Optional[float] = None
    qty: int
    entry_date: Optional[str] = None
    reason: Optional[str] = ""
    emotion: Optional[str] = "Calm"
    status: Optional[str] = "OPEN"
    pnl: Optional[float] = None


@app.post("/api/journal")
@limiter.limit("10/minute")
async def create_journal(
    entry: JournalEntryCreate, request: Request, _=Depends(require_session)
):
    try:
        row_id = db.add_journal_entry(entry.dict())
        return {"status": "success", "id": row_id}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/journal")
async def list_journal(request: Request, _=Depends(require_session)):
    try:
        return db.get_journal_entries()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/journal/{entry_id}")
async def delete_journal_entry(entry_id: int, request: Request, _=Depends(require_session)):
    try:
        success = db.delete_journal_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Predictions Tracking API ──────────────────────────────────────────────────


class PredictionCreate(BaseModel):
    symbol: str
    prediction_type: str  # 'UP' or 'DOWN'
    entry_price: float
    target_price: float
    stop_loss: float
    confidence_score: int
    rsi: Optional[float] = None
    macd: Optional[float] = None
    adx: Optional[float] = None
    reason: Optional[str] = ""


class PredictionResolve(BaseModel):
    actual_outcome: float
    status: str  # 'CORRECT' or 'INCORRECT' or 'FLAT'


@app.post("/api/predictions")
@limiter.limit("20/minute")
async def create_prediction(
    pred: PredictionCreate, request: Request, _=Depends(require_session)
):
    try:
        row_id = db.add_prediction(pred.dict())
        return {"status": "success", "id": row_id}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/predictions")
async def list_predictions(request: Request, _=Depends(require_session)):
    try:
        return db.get_predictions()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/predictions/{pred_id}/resolve")
async def resolve_prediction_route(
    pred_id: int, req: PredictionResolve, request: Request, _=Depends(require_session)
):
    try:
        success = db.resolve_prediction(pred_id, req.actual_outcome, req.status)
        if not success:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/predictions/{pred_id}")
async def delete_prediction_route(
    pred_id: int, request: Request, _=Depends(require_session)
):
    try:
        success = db.delete_prediction(pred_id)
        if not success:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/predictions/stats")
async def get_prediction_stats(request: Request, _=Depends(require_session)):
    try:
        preds = db.get_predictions()
        resolved = [p for p in preds if p["status"] not in ("PENDING", "ACTIVE")]
        
        # Fetch from high-performance cache
        cache = db.get_metrics_cache("dashboard_metrics") or {}
        
        # Calculate recent outcomes for the sparkline chart
        recent_outcomes = [p["status"].upper() in ("CORRECT", "WIN") for p in resolved[:20]]
        avg_conf = round(sum(p["confidence_score"] for p in preds) / len(preds), 1) if preds else 0.0
        
        # Get machine learning pattern rates
        pattern_success_rates = db.get_pattern_success_rates()
        
        win_rate = round((sum(1 for p in resolved if p["status"].upper() in ("CORRECT", "WIN")) / len(resolved)) * 100, 1) if resolved else 0.0
        
        return {
            "total_predictions": len(preds),
            "resolved_predictions": len(resolved),
            "win_rate": win_rate,
            "profit_factor": cache.get("profit_factor", 0.0),
            "empirical_rr_ratio": cache.get("avg_r", 0.0),
            "expected_value_pct": cache.get("ev_pct", 0.0),
            "max_drawdown_pct": cache.get("max_drawdown", 0.0),
            "average_win_pct": 0.0,  # Deprecated in favor of Avg R
            "average_loss_pct": 0.0, # Deprecated in favor of Avg R
            "best_sector": "N/A",    # Handled by strategy leaderboard
            "worst_sector": "N/A",   # Handled by strategy leaderboard
            "recent_outcomes": recent_outcomes,
            "avg_confidence": avg_conf,
            "pattern_success_rates": pattern_success_rates,
            "leaderboard": cache.get("leaderboard", [])
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/market_brief")
async def get_market_brief(request: Request, _=Depends(require_session)):
    try:
        # Get latest indicators via scan
        try:
            loop = asyncio.get_event_loop()
            signals = await loop.run_in_executor(
                _executor,
                functools.partial(sig_engine.run_scan, sig_engine.NSE_WATCHLIST),
            )
        except Exception:
            signals = []

        buys = [s for s in signals if s.get("signal") in ("BUY", "WEAK BUY")]
        sentiment_pct = int(len(buys) / len(signals) * 100) if signals else 50

        # Find best Opportunities
        top_ops = [
            s
            for s in signals
            if s.get("signal") in ("BUY", "SELL", "WEAK BUY", "WEAK SELL")
        ]
        top_ops.sort(key=lambda x: -x.get("confidence", 0))

        # Nifty overall trend based on watchlist sentiment
        if sentiment_pct >= 60:
            trend_bias = "BULLISH"
            heuristic_brief = "NSE watchlist indicators show broad buying conviction. Major components are holding short-term support lines (EMA9/VWAP) with expanding volume flow, signaling solid upside momentum."
        elif sentiment_pct <= 40:
            trend_bias = "BEARISH"
            heuristic_brief = "Bearish pressures dominate short-term structures. Heavyweight components are trading below daily VWAP averages with negative MACD histogram momentum, recommending caution."
        else:
            trend_bias = "CONSOLIDATION"
            heuristic_brief = "Sideways consolidation range observed. Low trend strength (ADX under 20) with prices clustering near middle Bollinger Band levels. Favor range-bound mean-reversion tactics."

        briefing_text = heuristic_brief

        # Try to generate using Gemini if available
        if _genai_client and signals:
            try:
                opp_summary = "\n".join(
                    f"- {s['symbol'].replace('.NS', '')}: {s['signal']} (Conf: {s['confidence']}%, Price: ₹{s['price']:.1f}, Reasoning: {s['reasoning']})"
                    for s in signals[:5]
                )
                prompt = (
                    f"You are a professional quantitative research strategist. Based on the NSE stock watchlist technical "
                    f"indicators below, write a 1-paragraph market overview briefing (max 90 words) summarizing nifty trend bias, "
                    f"overall sentiment levels, and top options. Avoid direct financial advice. Keep it concise, do not start with introductory text.\n\n"
                    f"--- WATCHLIST SCAN CONTEXT ---\n"
                    f"{opp_summary}\n"
                    f"-------------------------------\n\n"
                    f"Actionable quantitative analysis:"
                )
                response = _genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                gemini_text = response.text.strip()
                if gemini_text:
                    briefing_text = gemini_text
            except Exception:
                pass  # Fall back to heuristic

        return {
            "nifty_trend": trend_bias,
            "market_sentiment_pct": sentiment_pct,
            "top_opportunities": [
                {
                    "symbol": s["symbol"].replace(".NS", ""),
                    "name": s["name"],
                    "signal": s["signal"],
                    "confidence": s["confidence"],
                    "price": s["price"],
                }
                for s in top_ops[:3]
            ],
            "risk_events": [
                "RBI Monetary Policy Committee Rate Announcement (Upcoming)",
                "US Core CPI inflation data report (Scheduled release)",
                "Nifty Index Weekly Options Expiry (Thursday)",
                "Federal Reserve Open Market Committee Interest Rate decision",
            ],
            "briefing_text": briefing_text,
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# ── Historical Backtesting Endpoints ──────────────────────────────────────────

class SimRequest(BaseModel):
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"

@app.post("/api/admin/run-simulation")
async def run_historical_simulation(
    req: SimRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin)
):
    """
    Run historical backtesting simulation (ADMIN ONLY)
    
    Args:
        req: Start date and End date in JSON body.
    """
    start_date = req.start_date
    end_date = req.end_date
    
    # Validate dates
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Check if simulation is already running
    if simulation_status.is_running:
        raise HTTPException(
            status_code=409, 
            detail="Simulation already in progress"
        )
    
    # Start background task
    background_tasks.add_task(
        run_simulation_task, 
        start_date, 
        end_date,
        "admin"
    )
    
    return {
        "status": "started",
        "message": f"Simulating {start_date} to {end_date}",
        "initiated_by": "admin",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/admin/simulation-status")
async def get_simulation_status(current_user: dict = Depends(require_admin)):
    """Get current simulation progress"""
    return {
        "is_running": simulation_status.is_running,
        "progress": simulation_status.progress,
        "current_symbol": simulation_status.current_symbol,
        "stats": simulation_status.stats
    }

