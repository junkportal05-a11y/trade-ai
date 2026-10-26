"""Quotes, history, and market data router."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.core.config import settings
from app.core.constants import VALID_INTERVALS, VALID_RANGES
from app.models.schemas import (
    HistoryResponse,
    QuoteResponse,
    SearchResponse,
    HistoryParams,
    SearchRequest,
    QuoteRequest,
)
from app.services.quotes import get_symbol_quote
from signals import generate_synthetic_candles
from app.core.logging import logger
from app.core.executors import quote_executor
from app.core.limiter import limiter

router = APIRouter(prefix="/api", tags=["quotes"])


@router.get("/", response_model=dict)
@limiter.limit(settings.rate_limit_public)
def root(request: Request, _=SessionDep) -> dict:
    return {"status": "ok", "message": "Trading Platform API is running"}


@router.get("/keepalive", response_model=dict)
@limiter.limit(settings.rate_limit_public)
def keep_alive(request: Request, _=SessionDep) -> dict:
    from datetime import datetime, timezone, timedelta
    from app.services.market_hours import is_nse_market_open

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    market_open = is_nse_market_open()

    return {
        "status": "active",
        "message": "ApexTrade keep-alive handshake successful.",
        "current_time_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
        "market_status": "OPEN" if market_open else "CLOSED",
    }


_FALLBACK_PRICES = {
    "YESBANK.NS": 25.0,
    "TATASTEEL.NS": 170.0,
    "BANKBARODA.NS": 280.0,
    "TATAPOWER.NS": 445.0,
    "SBIN.NS": 830.0,
}


@router.get("/prices", response_model=dict)
@limiter.limit(settings.rate_limit_public)
async def get_live_prices(request: Request, symbols: str = "") -> dict:
    """HTTP fallback for the price WebSocket (simulated ticks, not exchange data)."""
    import random
    from datetime import datetime, timezone, timedelta

    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()][:50]
    if not requested:
        requested = list(_FALLBACK_PRICES)

    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    data = []
    for symbol in requested:
        base_price = _FALLBACK_PRICES.get(symbol, 100.0)
        data.append(
            {
                "symbol": symbol,
                "price": round(base_price * (1 + random.uniform(-0.003, 0.003)), 2),
                "prev_close": base_price,
                "timestamp": now_ist.isoformat(),
            }
        )
    return {
        "type": "tick",
        "simulated": True,
        "data_source": "SIMULATED",
        "data": data,
    }


@router.get("/quote", response_model=QuoteResponse)
@limiter.limit(settings.rate_limit_public)
async def get_quote(
    request: Request, req: QuoteRequest = Depends(QuoteRequest), db: Session = DbDep, _=SessionDep
) -> dict:
    # Validate symbol again via model; it's already uppercase due to validator
    symbol = req.symbol
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        quote_executor, lambda: get_symbol_quote(symbol)
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result


@router.get("/history", response_model=HistoryResponse)
@limiter.limit(settings.rate_limit_public)
def get_history(
    request: Request,
    params: HistoryParams = Depends(HistoryParams),
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.market_data import download_market_data_df

    # Validate interval and range against allowed constants
    if params.interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400, detail=f"Invalid interval. Choose from: {VALID_INTERVALS}"
        )
    if params.range not in VALID_RANGES:
        raise HTTPException(
            status_code=400, detail=f"Invalid range. Choose from: {VALID_RANGES}"
        )

    # CandleChart always needs renderable bars: any feeder failure falls through
    # to the synthetic generator instead of an HTTP 404/500.
    df = None
    try:
        df = download_market_data_df(
            params.symbol, period=params.range, interval=params.interval
        )
    except Exception as exc:
        logger.warning(f"[history] download failed for {params.symbol}: {exc}")

    fallback = False
    if df is None or df.empty:
        df = generate_synthetic_candles(params.symbol, params.range, params.interval)
        fallback = True
        logger.warning(
            f"[history] synthetic fallback generated for {params.symbol} "
            f"({params.interval}, {params.range})"
        )

    # Ensure column names are capitalized (handle yfinance lowercase columns)
    try:
        df.columns = [str(c).capitalize() for c in df.columns]
    except Exception:
        pass  # Columns already in correct format or unexpected type

    required_cols = ["Open", "High", "Low", "Close"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        logger.warning(f"[history] malformed columns for {params.symbol}: {missing}")
        df = generate_synthetic_candles(params.symbol, params.range, params.interval)
        fallback = True

    df = df.dropna(subset=required_cols)
    if df.empty:
        logger.warning(f"[history] all-NaN candles for {params.symbol}, using synthetic")
        df = generate_synthetic_candles(params.symbol, params.range, params.interval)
        fallback = True

    use_unix = params.interval not in {"1d", "5d", "1wk", "1mo", "3mo"}
    bars = []
    for row in df.itertuples():
        t = int(row.Index.timestamp()) if use_unix else row.Index.strftime("%Y-%m-%d")
        bars.append(
            {
                "time": t,
                "open": round(float(row.Open), 4),
                "high": round(float(row.High), 4),
                "low": round(float(row.Low), 4),
                "close": round(float(row.Close), 4),
                "volume": int(getattr(row, "Volume", 0)),
            }
        )

    return {
        "symbol": params.symbol.upper(),
        "interval": params.interval,
        "range": params.range,
        "count": len(bars),
        "bars": bars,
        "fallback": fallback,
    }


@router.get("/search", response_model=SearchResponse)
@limiter.limit(settings.rate_limit_public)
async def search_symbols(
    request: Request, req: SearchRequest = Depends(SearchRequest), db: Session = DbDep, _=SessionDep
) -> dict:
    from app.services.broker import get_broker_feed

    symbol = req.q.upper().strip().replace(".NS", "")
    key = get_broker_feed().get_instrument_token(symbol)
    if key:
        return {
            "results": [{"symbol": symbol + ".NS", "name": req.q, "type": "NSE Equity"}]
        }
    return {"results": []}
