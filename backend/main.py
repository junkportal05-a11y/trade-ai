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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends, Header
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

load_dotenv()



limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="ApexTrade API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://trade-ai-beta.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

from auth_helpers import (
    require_admin,
    require_session,
    create_session,
    cleanup_sessions,
    ACTIVE_SESSIONS,
    SESSION_TTL,
    ADMIN_KEY,
    USER_REGISTRY,
    authenticate_user
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
async def login(req: LoginRequest, request: Request):
    u = req.username.strip()
    user_obj = authenticate_user(u, req.password)
    if not user_obj:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(u)
    return {
        "token": token,
        "username": u,
        "role": user_obj["role"],
        "clearance": user_obj["clearance"],
        "expires_in": SESSION_TTL
    }

@app.post("/api/logout")
async def logout(x_session_token: str = Header(None)):
    if x_session_token and x_session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[x_session_token]
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
    Keep-alive endpoint to prevent Render free tier cold starts.
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
            "purpose": "Keeps backend node warm during NSE trading session to eliminate 5m candle latency."
        }
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
            detail="Upstox API key or Redirect URI not configured in the environment."
        )
    url = upstox_feed.get_login_url(state or "")
    return RedirectResponse(url)


@app.get("/api/upstox/callback")
def upstox_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    res = upstox_feed.exchange_code_for_token(code)
    if not res:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code for access token")
    
    redirect_target = state or ""
    if not redirect_target:
        redirect_uri = upstox_feed.UPSTOX_REDIRECT_URI
        if "localhost" in redirect_uri:
            redirect_target = "http://localhost:5173/account"
        else:
            redirect_target = "https://trade-ai-beta.vercel.app/account"
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
        
    return RedirectResponse(redirect_target)


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
            with open(upstox_feed.TOKEN_FILE, "r") as f:
                data = json.load(f)
                status_data["updated_at"] = data.get("updated_at")
                status_data["user_name"] = data.get("user_name")
        except Exception:
            pass
    return status_data


@app.get("/api/history")
def get_history(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    interval: str = Query("1d", description="Bar interval: 1m,5m,15m,30m,1h,1d,1wk,1mo"),
    range: str = Query("3mo", description="Date range: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max"),
):
    """
    Returns OHLCV candlestick bars ready for TradingView Lightweight Charts.

    Lightweight Charts expects:
      { time: 'YYYY-MM-DD' | unix_timestamp, open, high, low, close, volume }
    """
    VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}
    VALID_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}

    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Invalid interval. Choose from: {VALID_INTERVALS}")
    if range not in VALID_RANGES:
        raise HTTPException(status_code=400, detail=f"Invalid range. Choose from: {VALID_RANGES}")

    try:
        df = sig_engine.download_market_data_df(symbol, period=range, interval=interval)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No history for {symbol}")

        # Drop NaN values in OHLC columns to prevent JSON serialization crash
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No history data found for {symbol} after filtering NaNs")

        # For intraday intervals, use Unix timestamps; for daily+, use date strings
        use_unix = interval not in {"1d", "5d", "1wk", "1mo", "3mo"}

        bars = []
        for ts, row in df.iterrows():
            if use_unix:
                t = int(ts.timestamp())
            else:
                t = ts.strftime("%Y-%m-%d")

            bars.append({
                "time": t,
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })

        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "range": range,
            "count": len(bars),
            "bars": bars,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

_executor = ThreadPoolExecutor(max_workers=8)


@app.get("/api/signals")
@limiter.limit("5/minute")
async def get_signals(
    request: Request,
    symbols: Optional[str] = Query(None, description="Comma-separated NSE symbols, e.g. RELIANCE.NS,TCS.NS. Omit for full scan."),
    limit:   int = Query(20, ge=1, le=50, description="Max results to return"),
    _=Depends(require_session)
):
    """
    Scans NSE stocks and returns ranked intraday signals.
    Each signal includes: BUY/SELL/HOLD, confidence %, entry, target, stop-loss, R:R ratio, reasoning.
    """
    loop = asyncio.get_event_loop()

    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        # Map to watchlist entries or create minimal ones
        wl_map   = {w["symbol"]: w for w in sig_engine.NSE_WATCHLIST}
        watchlist = [wl_map.get(s, {"symbol": s, "name": s.replace(".NS", ""), "sector": "NSE"}) for s in sym_list]
    else:
        watchlist = sig_engine.NSE_WATCHLIST

    # Run analysis concurrently in thread pool (scanning is blocking I/O)
    import functools
    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                functools.partial(sig_engine.run_scan, watchlist),
            ),
            timeout=150
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
        "signals":     results[:limit],
        "disclaimer":  "Algorithmic signals only — not financial advice. Always apply your own judgement and risk management.",
    }


@app.get("/api/signal/{symbol}")
async def get_signal_single(symbol: str):
    """
    Full technical analysis for a single NSE symbol.
    Accepts symbol with or without .NS suffix.
    """
    sym = symbol.upper()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"

    wl_map = {w["symbol"]: w for w in sig_engine.NSE_WATCHLIST}
    meta   = wl_map.get(sym, {"symbol": sym, "name": sym.replace(".NS", ""), "sector": "NSE"})

    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        lambda: sig_engine.analyse_symbol(meta["symbol"], meta["name"], meta["sector"]),
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {sym}. Market may be closed or symbol invalid.")

    return result



class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None  # { symbol, price, change_pct, ... }
    history: Optional[List[ChatMessage]] = None


@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat(req: ChatRequest, request: Request, _=Depends(require_session)):
    """
    AI trading assistant. Uses Gemini if GEMINI_API_KEY is set,
    otherwise falls back to a context-aware heuristic engine.
    """
    symbol  = (req.context or {}).get("symbol", "the market")
    price   = (req.context or {}).get("price", None)
    chg_pct = (req.context or {}).get("changePct", None)

    # ── Try Gemini (google-genai SDK) ────────────────────────────────────────
    if _genai_client:
        try:
            # Load custom trading knowledge base
            knowledge_content = ""
            knowledge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "trading_knowledge.txt"))
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
            
            prompt = f"{system_ctx}\n\n{formatted_history}User: {req.message}\nAssistant:"
            
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
    chg_str   = f"{chg_pct:+.2f}%" if chg_pct is not None else "unchanged"

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
    elif any(w in msg_lower for w in ["stop", "sl", "risk", "size", "sizing", "capital", "money"]):
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
    'HAL.NS': 4550.0,
    'BEL.NS': 295.0,
    'RVNL.NS': 385.0,
    'IREDA.NS': 185.0,
    'HUDCO.NS': 275.0,
    'COALINDIA.NS': 485.0,
    'NHPC.NS': 95.0,
    'ADANIPORTS.NS': 1405.0,
    'TATAPOWER.NS': 445.0,
    'BHEL.NS': 305.0,
}

# Live prices cache seeded initially with baseline seed prices
LIVE_PRICES_CACHE = {
    sym: {
        "price": price,
        "prev_close": price,
        "timestamp": int(time.time() * 1000)
    } for sym, price in SEED_PRICES.items()
}

_crawl_executor = ThreadPoolExecutor(max_workers=5)


async def fetch_live_quotes_loop():
    """
    Background crawler task that runs every 10 seconds to fetch the latest
    quotes for all watchlisted NSE stocks and updates LIVE_PRICES_CACHE.
    """
    import functools
    import requests
    import pandas as pd
    watchlist_symbols = [w["symbol"] for w in sig_engine.NSE_WATCHLIST]
    
    while True:
        # Preserve API rate limits / credits when no active users are online
        if len(active_connections) == 0:
            await asyncio.sleep(5)
            continue

        sleep_time = 10
        try:
            loop = asyncio.get_event_loop()
            
            if upstox_feed.is_authorized():
                # Fetch live quotes from Upstox
                quotes = await loop.run_in_executor(
                    _crawl_executor,
                    functools.partial(upstox_feed.get_live_quotes, watchlist_symbols)
                )
                if quotes:
                    for sym in watchlist_symbols:
                        quote = quotes.get(sym)
                        if quote:
                            data = {
                                "price": quote["price"],
                                "prev_close": quote["prev_close"],
                                "timestamp": int(time.time() * 1000)
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
            db.update_signal_status(sig["id"], status, exit_price, pnl)
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
                is_past_market_close = now_ist.hour > 15 or (now_ist.hour == 15 and now_ist.minute >= 30)
                
                if is_future_day or (now_ist.date() == scanned_dt_ist.date() and is_past_market_close):
                    pnl_calc = 0.0
                    if "BUY" in signal_type:
                        pnl_calc = (current_price - entry_price) / entry_price * 100
                    else:
                        pnl_calc = (entry_price - current_price) / entry_price * 100
                        
                    db.update_signal_status(sig["id"], "EXPIRED", current_price, pnl_calc)
            else:
                # OVERNIGHT: 5 days limit
                days_diff = (now_utc - scanned_dt_utc).days
                if days_diff >= 5:
                    pnl_calc = 0.0
                    if "BUY" in signal_type:
                        pnl_calc = (current_price - entry_price) / entry_price * 100
                    else:
                        pnl_calc = (entry_price - current_price) / entry_price * 100
                        
                    db.update_signal_status(sig["id"], "EXPIRED", current_price, pnl_calc)
        except Exception:
            pass


AUTO_SCAN_INTERVAL_OPEN   = 60
AUTO_SCAN_INTERVAL_CLOSED = 3600

async def auto_scan_loop():
    """
    Background task:
      - Market OPEN  → scan every 60 s, log signals to DB
      - Market CLOSED → scan every 60 min for overnight signals
    Also reconciles pending signals against LIVE_PRICES_CACHE every cycle.
    """
    import functools
    loop = asyncio.get_event_loop()

    while True:
        try:
            market_open = is_nse_market_open()
            scan_type   = "INTRADAY" if market_open else "OVERNIGHT"

            # ── 1. Run signal scan ───────────────────────────────────────────
            results = await loop.run_in_executor(
                _executor,
                functools.partial(sig_engine.run_scan, sig_engine.NSE_WATCHLIST),
            )

            # Log BUY / SELL signals with confidence >= 60
            for sig in results:
                if sig.get("signal") in ("BUY", "SELL") and sig.get("confidence", 0) >= 60:
                    sig["direction"]  = sig["signal"]
                    sig["entry"]      = sig.get("price",      sig.get("entry", 0))
                    sig["scan_type"]  = scan_type
                    db.add_signal(sig)

            # ── 2. Reconcile pending signals vs live prices ──────────────────
            pending = db.get_pending_signals()
            for trade in pending:
                live = LIVE_PRICES_CACHE.get(trade["symbol"])
                if live is None:
                    continue

                price  = live["price"]
                is_buy = "BUY" in trade["signal_type"]

                hit_target = (is_buy  and price >= trade["target"]) or \
                             (not is_buy and price <= trade["target"])
                hit_stop   = (is_buy  and price <= trade["stop_loss"]) or \
                             (not is_buy and price >= trade["stop_loss"])

                if hit_target:
                    pnl = db._calc_pnl(trade["signal_type"], trade["entry_price"], price)
                    db.update_signal(trade["id"], "HIT_TARGET", price, pnl)
                elif hit_stop:
                    pnl = db._calc_pnl(trade["signal_type"], trade["entry_price"], price)
                    db.update_signal(trade["id"], "HIT_STOP", price, pnl)

            # ── 3. Expire stale intraday signals ─────────────────────────────
            db.expire_old_intraday()

        except Exception as e:
            print(f"[auto_scan_loop] error: {e}")

        sleep_dur = AUTO_SCAN_INTERVAL_OPEN if is_nse_market_open() else AUTO_SCAN_INTERVAL_CLOSED
        await asyncio.sleep(sleep_dur)


@app.on_event("startup")
async def startup_event():
    db.init_db()
    asyncio.create_task(fetch_live_quotes_loop())
    asyncio.create_task(auto_scan_loop())


@app.websocket("/ws/prices")
async def websocket_prices(
    websocket: WebSocket,
    token: str = Query(None),
    symbols: str = "HAL.NS,BEL.NS,RVNL.NS,IREDA.NS,HUDCO.NS,COALINDIA.NS,NHPC.NS,ADANIPORTS.NS,TATAPOWER.NS,BHEL.NS"
):
    await websocket.accept()
    if not token or token not in ACTIVE_SESSIONS:
        await websocket.close(code=4001)
        return

    active_connections.append(websocket)

    watch = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    
    # Store local tracking price states to simulate smooth tick transitions
    local_prices: dict[str, float] = {}
    local_prev_closes: dict[str, float] = {}

    for sym in watch:
        cached = LIVE_PRICES_CACHE.get(sym, {"price": SEED_PRICES.get(sym, 150.0), "prev_close": SEED_PRICES.get(sym, 150.0)})
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
                            cached = LIVE_PRICES_CACHE.get(sym, {"price": SEED_PRICES.get(sym, 150.0), "prev_close": SEED_PRICES.get(sym, 150.0)})
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

                ticks.append({
                    "symbol": sym,
                    "price": round(price, 4),
                    "prev_close": round(local_prev_closes.get(sym, price), 4),
                    "timestamp": int(time.time() * 1000),
                })

            await websocket.send_json({
                "type": "tick",
                "data": ticks,
                "market_status": "OPEN" if market_open else "CLOSED"
            })
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
async def allocate_capital(req: CapitalRequest, request: Request, _=Depends(require_session)):
    """
    Scan HIGH_VOLATILITY_UNIVERSE matched to capital size.
    Small capital → cheap volatile stocks (YESBANK, SUZLON, RVNL…)
    Large capital → full universe including mid/large caps.
    """
    if req.capital < 500:
        raise HTTPException(status_code=400, detail="Minimum capital is ₹500")

    import functools
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
                    req.capital
                ),
            ),
            timeout=150
        )
    except asyncio.TimeoutError:
        return {
            "error": "Scan took too long (backend cold start)",
            "positions": [],
            "message": "First scan on free tier takes 2 min. Try again in 30s when backend is warm."
        }

    # Normalise signal fields so allocator can read them
    normalised = []
    for s in signals:
        normalised.append({
            **s,
            "direction":   s.get("signal", s.get("direction", "")),
            "entry":       s.get("price", s.get("entry", s.get("entry_price", 0))),
            "entry_price": s.get("price", s.get("entry", s.get("entry_price", 0))),
        })

    plan = capital_allocator.allocate(
        req.capital,
        normalised,
        style=req.trading_style,
        risk=req.risk_level,
        max_recommendations=req.max_recommendations
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
                "reason": ", ".join(pos.get("reasons", []))
            }
            db.add_prediction(pred_data)
        except Exception as e:
            print(f"[api/allocate] Error archiving recommendation for {pos['symbol']}: {e}")

    return plan


@app.post("/api/allocate/quick")
@limiter.limit("3/minute")
async def allocate_capital_quick(req: CapitalRequest, request: Request, _=Depends(require_session)):
    """
    Fast allocation using already-cached live prices (no fresh yfinance scan).
    Returns instantly if LIVE_PRICES_CACHE is warm; falls back to full scan otherwise.
    """
    if req.capital < 500:
        raise HTTPException(
            status_code=400,
            detail="Minimum capital is ₹500"
        )

    # Build lightweight signals from the live price cache
    quick_signals = []
    for entry in sig_engine.NSE_WATCHLIST:
        sym   = entry["symbol"]
        
        # Apply segment filter
        if req.market_segment == "BSE" and not sym.endswith(".BO"):
            continue
        elif req.market_segment == "F&O" and sym not in ["HAL.NS", "BEL.NS", "RVNL.NS", "COALINDIA.NS", "ADANIPORTS.NS", "TATAPOWER.NS", "BHEL.NS"]:
            continue

        cached = LIVE_PRICES_CACHE.get(sym)
        if not cached:
            continue
        price = cached["price"]
        quick_signals.append({
            "symbol":     sym,
            "name":       entry["name"],
            "sector":     entry["sector"],
            "direction":  "BUY",   # optimistic placeholder
            "entry":      price,
            "entry_price": price,
            "target":     round(price * 1.025, 2),
            "target1":    round(price * 1.025, 2),
            "target2":    round(price * 1.045, 2),
            "stop_loss":  round(price * 0.985, 2),
            "confidence": 60,
            "atr":        round(price * 0.012, 2),
            "rr_ratio":   1.67,
            "rsi":        50,
            "macd_hist":  0.0,
            "adx":        20,
            "reasons":    ["Cached Live Price Signal"],
            "sector_strength": "Medium",
            "expected_move_pct": 2.5,
        })

    if not quick_signals:
        # Cache not warm yet — fall back to full scan
        return await allocate_capital(req)

    plan = capital_allocator.allocate(
        req.capital,
        quick_signals,
        style=req.trading_style,
        risk=req.risk_level,
        max_recommendations=req.max_recommendations
    )
    plan["all_signals"] = quick_signals
    plan["note"] = "Quick allocation using cached prices — run /api/allocate for a full fresh scan."

    # Log generated recommendations in predictions_history database
    for pos in plan.get("positions", []):
        try:
            pred_data = {
                "symbol": pos["symbol"],
                "prediction_type": "UP",
                "entry_price": pos["entry_price"],
                "target_price": pos["target1"],
                "stop_loss": pos["stop_loss"],
                "confidence_score": pos["confidence"],
                "rsi": pos.get("rsi"),
                "macd": pos.get("macd_hist"),
                "adx": pos.get("adx"),
                "status": "PENDING",
                "reason": ", ".join(pos.get("reasons", []))
            }
            db.add_prediction(pred_data)
        except Exception as e:
            print(f"[api/allocate/quick] Error archiving recommendation for {pos['symbol']}: {e}")

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
async def create_journal(entry: JournalEntryCreate, request: Request, _=Depends(require_session)):
    try:
        row_id = db.add_journal_entry(entry.dict())
        return {"status": "success", "id": row_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/journal")
async def list_journal(request: Request, _=Depends(require_session)):
    try:
        return db.get_journal_entries()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        if not success:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
async def create_prediction(pred: PredictionCreate, request: Request, _=Depends(require_session)):
    try:
        row_id = db.add_prediction(pred.dict())
        return {"status": "success", "id": row_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/predictions")
async def list_predictions(request: Request, _=Depends(require_session)):
    try:
        return db.get_predictions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predictions/{pred_id}/resolve")
async def resolve_prediction_route(pred_id: int, req: PredictionResolve, request: Request, _=Depends(require_session)):
    try:
        success = db.resolve_prediction(pred_id, req.actual_outcome, req.status)
        if not success:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/predictions/{pred_id}")
async def delete_prediction_route(pred_id: int, request: Request, _=Depends(require_session)):
    try:
        success = db.delete_prediction(pred_id)
        if not success:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/predictions/stats")
async def get_prediction_stats(request: Request, _=Depends(require_session)):
    try:
        preds = db.get_predictions()
        resolved = [p for p in preds if p["status"] != "PENDING"]
        correct = [p for p in resolved if p["status"] == "CORRECT"]
        
        win_rate = round((len(correct) / len(resolved)) * 100, 1) if len(resolved) > 0 else 0.0
        
        # Calculate Mean Absolute Error (MAE) between target and actual resolved price
        total_error = 0.0
        for p in resolved:
            actual = p.get("actual_outcome")
            target = p.get("target_price")
            if actual is not None and target is not None:
                total_error += abs(target - actual)
        avg_error = round(total_error / len(resolved), 2) if len(resolved) > 0 else 0.0
        
        # Best and worst sectors
        SECTORS_MAP = {
            'HAL.NS': 'Defence', 'BEL.NS': 'Defence', 'RVNL.NS': 'Railways',
            'IREDA.NS': 'Green Energy', 'HUDCO.NS': 'Finance', 'COALINDIA.NS': 'Energy',
            'NHPC.NS': 'Power', 'ADANIPORTS.NS': 'Infrastructure', 'TATAPOWER.NS': 'Power',
            'BHEL.NS': 'Capital Goods'
        }
        
        sector_wins = {}
        sector_totals = {}
        for p in resolved:
            sec = SECTORS_MAP.get(p['symbol'], 'Other')
            sector_totals[sec] = sector_totals.get(sec, 0) + 1
            if p['status'] == 'CORRECT':
                sector_wins[sec] = sector_wins.get(sec, 0) + 1
                
        best_sector = "None"
        best_rate = -1.0
        worst_sector = "None"
        worst_rate = 101.0
        
        for sec, total in sector_totals.items():
            rate = (sector_wins.get(sec, 0) / total) * 100
            if rate > best_rate:
                best_rate = rate
                best_sector = f"{sec} ({rate:.0f}%)"
            if rate < worst_rate:
                worst_rate = rate
                worst_sector = f"{sec} ({rate:.0f}%)"
                
        # outcomes list for sparkline (last 20 resolved outcomes)
        recent_outcomes = [p["status"] == "CORRECT" for p in resolved[:20]]
        
        # Average confidence of predictions
        avg_conf = round(sum(p["confidence_score"] for p in preds) / len(preds), 1) if len(preds) > 0 else 0.0
        
        return {
            "total_predictions": len(preds),
            "resolved_predictions": len(resolved),
            "win_rate": win_rate,
            "avg_error": avg_error,
            "best_sector": best_sector if best_rate >= 0 else "N/A",
            "worst_sector": worst_sector if worst_rate <= 100 else "N/A",
            "recent_outcomes": recent_outcomes,
            "avg_confidence": avg_conf
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market_brief")
async def get_market_brief(request: Request, _=Depends(require_session)):
    try:
        # Get latest indicators via scan
        try:
            signals = sig_engine.run_scan()
        except Exception:
            signals = []
            
        buys = [s for s in signals if s.get("signal") in ("BUY", "WEAK BUY")]
        sentiment_pct = int(len(buys) / len(signals) * 100) if signals else 50
        
        # Find best Opportunities
        top_ops = [s for s in signals if s.get("signal") in ("BUY", "SELL", "WEAK BUY", "WEAK SELL")]
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
                    f"- {s['symbol'].replace('.NS','')}: {s['signal']} (Conf: {s['confidence']}%, Price: ₹{s['price']:.1f}, Reasoning: {s['reasoning']})"
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
                pass # Fall back to heuristic
                
        return {
            "nifty_trend": trend_bias,
            "market_sentiment_pct": sentiment_pct,
            "top_opportunities": [
                {
                    "symbol": s["symbol"].replace('.NS', ''),
                    "name": s["name"],
                    "signal": s["signal"],
                    "confidence": s["confidence"],
                    "price": s["price"]
                }
                for s in top_ops[:3]
            ],
            "risk_events": [
                "RBI Monetary Policy Committee Rate Announcement (Upcoming)",
                "US Core CPI inflation data report (Scheduled release)",
                "Nifty Index Weekly Options Expiry (Thursday)",
                "Federal Reserve Open Market Committee Interest Rate decision"
            ],
            "briefing_text": briefing_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

