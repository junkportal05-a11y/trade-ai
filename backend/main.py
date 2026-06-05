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
import db
import capital_allocator
from backtest_routes import backtest_router

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

# ── CORS: allow any origin for easy hosting ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtest_router)

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
            # Load custom trading knowledge base
            knowledge_content = ""
            knowledge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "trading_knowledge.txt"))
            if os.path.exists(knowledge_path):
                try:
                    with open(knowledge_path, "r", encoding="utf-8") as kf:
                        # Limit context size to avoid token limit issues, take first 40000 chars
                        knowledge_content = kf.read(40000)
                except Exception:
                    pass

            system_ctx = (
                f"You are an expert trading mentor and assistant embedded in the APEXTRADE platform. "
                f"You have been trained on the user's custom trading guides and PDFs (candlesticks, risk management, stop losses, etc.). "
                f"Use the following knowledge context to answer any trading query, explain strategies, and mentor the user: \n\n"
                f"--- KNOWLEDGE BASE EXTRACTS ---\n"
                f"{knowledge_content}\n"
                f"-------------------------------\n\n"
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


# Fallback seed prices for Indian stocks if yfinance fails
SEED_PRICES = {
    'RELIANCE.NS': 2920.0,
    'TCS.NS': 4100.0,
    'HDFCBANK.NS': 1780.0,
    'INFY.NS': 1650.0,
    'ICICIBANK.NS': 1290.0,
    'SBIN.NS': 845.0,
    'BAJFINANCE.NS': 7200.0,
    'TMPV.NS': 385.0,
    'WIPRO.NS': 490.0,
    'AXISBANK.NS': 1190.0,
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
    quotes for all watchlisted NSE stocks in a thread pool and updates LIVE_PRICES_CACHE.
    """
    import functools
    import pandas as pd
    watchlist_symbols = [w["symbol"] for w in sig_engine.NSE_WATCHLIST]
    
    while True:
        try:
            loop = asyncio.get_event_loop()
            
            # Fetch all symbols at once (bulk download is extremely fast)
            df = await loop.run_in_executor(
                _crawl_executor,
                functools.partial(
                    yf.download, 
                    tickers=" ".join(watchlist_symbols), 
                    period="1d", 
                    interval="1m", 
                    auto_adjust=True, 
                    progress=False
                )
            )
            
            if df is not None and not df.empty:
                is_multi = isinstance(df.columns, pd.MultiIndex)
                for sym in watchlist_symbols:
                    try:
                        if is_multi:
                            close_col = ('Close', sym)
                            open_col  = ('Open', sym)
                        else:
                            close_col = 'Close'
                            open_col  = 'Open'
                            
                        if (is_multi and close_col in df.columns) or (not is_multi and close_col in df.columns):
                            prices_series = df[close_col].dropna()
                            if not prices_series.empty:
                                last_price = float(prices_series.iloc[-1])
                                # Fallback prev_close is the first price (open of the day)
                                first_price = float(df[open_col].dropna().iloc[0]) if open_col in df.columns else last_price
                                LIVE_PRICES_CACHE[sym] = {
                                    "price": last_price,
                                    "prev_close": first_price,
                                    "timestamp": int(time.time() * 1000)
                                }
                    except Exception:
                        pass
        except Exception:
            pass
            
        # Reconcile pending signals after prices update
        try:
            reconcile_pending_signals()
        except Exception:
            pass
            
        await asyncio.sleep(10)


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
async def websocket_prices(websocket: WebSocket, symbols: str = "RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS,SBIN.NS,BAJFINANCE.NS,TMPV.NS,WIPRO.NS,AXISBANK.NS"):
    """
    Streams price ticks for the requested symbols.
    Simulates micro-ticks around live yfinance baseline prices when market is open.
    Sends static, non-fluctuating closing prices when market is closed.
    """
    await websocket.accept()
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
            ticks = []
            for sym in watch:
                cached = LIVE_PRICES_CACHE.get(sym)
                if cached:
                    baseline_price = cached["price"]
                    local_prev_closes[sym] = cached["prev_close"]
                else:
                    baseline_price = local_prices.get(sym, SEED_PRICES.get(sym, 150.0))

                if market_open:
                    # Stream simulated tick fluctuations around the live baseline price
                    price = _simulate_tick(baseline_price)
                    local_prices[sym] = price
                else:
                    # Gating: Closed market, stream static closing price without visual walk
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


@app.post("/api/allocate")
async def allocate_capital(req: CapitalRequest):
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
                functools.partial(sig_engine.run_scan, target_symbols),
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

    plan = capital_allocator.allocate(req.capital, normalised)
    plan["all_signals"] = normalised
    return plan


@app.post("/api/allocate/quick")
async def allocate_capital_quick(req: CapitalRequest):
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
            "stop_loss":  round(price * 0.985, 2),
            "confidence": 60,
            "atr":        round(price * 0.012, 2),
            "rr_ratio":   1.67,
        })

    if not quick_signals:
        # Cache not warm yet — fall back to full scan
        return await allocate_capital(req)

    plan = capital_allocator.allocate(req.capital, quick_signals)
    plan["all_signals"] = quick_signals
    plan["note"] = "Quick allocation using cached prices — run /api/allocate for a full fresh scan."
    return plan
