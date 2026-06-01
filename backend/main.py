"""
Trading Platform Backend - FastAPI + yfinance
Run with: uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Optional

import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import signals as sig_engine

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

app = FastAPI(title="Trading Platform API", version="1.0.0")

# ── CORS: allow your React dev server (Vite default: 5173, CRA: 3000) ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Active WebSocket connections ───────────────────────────────────────────────
active_connections: list[WebSocket] = []


# ══════════════════════════════════════════════════════════════════════════════
#  REST ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "ok", "message": "Trading Platform API is running"}


@app.get("/api/quote")
def get_quote(symbol: str = Query(..., description="Ticker symbol, e.g. AAPL")):
    """
    Returns current price, daily change, volume, and metadata for a symbol.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        # yfinance key names vary; fall back gracefully
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("ask")
            or info.get("bid")
        )
        if price is None:
            raise HTTPException(status_code=404, detail=f"No price data for {symbol}")

        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose", price)
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0.0

        return {
            "symbol": symbol.upper(),
            "name": info.get("shortName", symbol.upper()),
            "price": round(price, 4),
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "volume": info.get("regularMarketVolume", 0),
            "market_cap": info.get("marketCap"),
            "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        ticker = yf.Ticker(symbol.upper())
        df = ticker.history(period=range, interval=interval, auto_adjust=True)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No history data found for {symbol}")

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
    Quick symbol search. yfinance doesn't have a real search API,
    so we validate by attempting to fetch the ticker's fast_info.
    Replace this with a real search API (e.g. Alpaca, Finnhub) for production.
    """
    symbol = q.upper().strip()
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            return {"results": []}
        return {
            "results": [
                {
                    "symbol": symbol,
                    "name": getattr(info, "currency", symbol),
                    "type": "Equity",
                }
            ]
        }
    except Exception:
        return {"results": []}


# ══════════════════════════════════════════════════════════════════════════════
#  NSE INTRADAY SIGNAL ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

_executor = ThreadPoolExecutor(max_workers=8)


@app.get("/api/signals")
async def get_signals(
    symbols: Optional[str] = Query(None, description="Comma-separated NSE symbols, e.g. RELIANCE.NS,TCS.NS. Omit for full scan."),
    limit:   int = Query(20, ge=1, le=50, description="Max results to return"),
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

    # Run analysis concurrently in thread pool (yfinance is blocking I/O)
    import functools
    results = await loop.run_in_executor(
        _executor,
        functools.partial(sig_engine.run_scan, watchlist),
    )

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



class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None  # { symbol, price, change_pct, ... }


@app.post("/api/chat")
async def chat(req: ChatRequest):
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
            system_ctx = (
                f"You are an expert trading assistant embedded in a professional trading platform. "
                f"The user is currently viewing {symbol}"
                + (f" trading at ₹{price:.2f}" if price else "")
                + (f" ({chg_pct:+.2f}% today)" if chg_pct is not None else "")
                + ". Provide concise, actionable analysis. "
                "Never provide financial advice — always remind the user this is educational. "
                "Keep responses under 150 words. Use **bold** sparingly for key terms."
            )
            prompt = f"{system_ctx}\n\nUser: {req.message}\nAssistant:"
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

    if any(w in msg_lower for w in ["buy", "long", "bullish", "upside"]):
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


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket, symbols: str = "AAPL,MSFT,GOOGL,TSLA"):
    """
    Streams simulated price ticks for the requested symbols.
    Send a JSON message to change the watched symbols:
        { "action": "subscribe", "symbols": ["AAPL", "NVDA"] }

    To replace with real data: swap the _simulate_tick() call with
    a Polygon.io / Alpaca WebSocket feed push.
    """
    await websocket.accept()
    active_connections.append(websocket)

    # Bootstrap: fetch real current prices for initial seed values
    watch = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    seed_prices: dict[str, float] = {}
    prev_closes: dict[str, float] = {}

    for sym in watch:
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            p = getattr(info, "last_price", None) or getattr(info, "regular_market_price", 100.0)
            seed_prices[sym] = float(p)
            pc = getattr(info, "previous_close", None) or p
            prev_closes[sym] = float(pc)
        except Exception:
            seed_prices[sym] = 100.0
            prev_closes[sym] = 100.0

    try:
        while True:
            # Check for incoming control messages (non-blocking)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                msg = json.loads(raw)
                if msg.get("action") == "subscribe" and "symbols" in msg:
                    new_syms = [s.strip().upper() for s in msg["symbols"] if s.strip()]
                    for sym in new_syms:
                        if sym not in seed_prices:
                            try:
                                t = yf.Ticker(sym)
                                info = t.fast_info
                                p = getattr(info, "last_price", None) or 100.0
                                seed_prices[sym] = float(p)
                                pc = getattr(info, "previous_close", None) or p
                                prev_closes[sym] = float(pc)
                            except Exception:
                                seed_prices[sym] = 100.0
                                prev_closes[sym] = 100.0
                    watch = new_syms
            except asyncio.TimeoutError:
                pass

            # Emit one tick per symbol
            market_open = is_nse_market_open()
            ticks = []
            for sym in watch:
                if market_open:
                    price = _simulate_tick(seed_prices[sym])
                    seed_prices[sym] = price
                else:
                    price = seed_prices[sym]
                ticks.append({
                    "symbol": sym,
                    "price": round(price, 4),
                    "prev_close": round(prev_closes.get(sym, price), 4),
                    "timestamp": int(time.time() * 1000),
                })

            await websocket.send_json({
                "type": "tick",
                "data": ticks,
                "market_status": "OPEN" if market_open else "CLOSED"
            })
            await asyncio.sleep(1)  # 1-second cadence; reduce for higher frequency

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
