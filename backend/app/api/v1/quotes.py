"""Quotes, history, and market data router."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep
from app.core.config import settings
from app.core.constants import VALID_INTERVALS, VALID_RANGES
from app.models.schemas import HistoryResponse, QuoteResponse, SearchResponse, HistoryParams, SearchRequest, QuoteRequest
from app.services.quotes import get_symbol_quote
from app.core.executors import quote_executor
from app.main import limiter

router = APIRouter(prefix="/api", tags=["quotes"])


@router.get("/", response_model=dict)
@limiter.limit(settings.rate_limit_public)
def root() -> dict:
    return {"status": "ok", "message": "Trading Platform API is running"}


@router.get("/keepalive", response_model=dict)
@limiter.limit(settings.rate_limit_public)
def keep_alive() -> dict:
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


@router.get("/quote", response_model=QuoteResponse)
@limiter.limit(settings.rate_limit_public)
async def get_quote(req: QuoteRequest = Depends(), db: Session = DbDep) -> dict:
    # Validate symbol again via model; it's already uppercase due to validator
    symbol = req.symbol
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        quote_executor,
        lambda: get_symbol_quote(symbol)
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result


@router.get("/history", response_model=HistoryResponse)
@limiter.limit(settings.rate_limit_public)
def get_history(params: HistoryParams = Depends(), db: Session = DbDep) -> dict:
    from app.services.market_data import download_market_data_df

    # Validate interval and range against allowed constants
    from app.core.constants import VALID_INTERVALS, VALID_RANGES
    if params.interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400, detail=f"Invalid interval. Choose from: {VALID_INTERVALS}"
        )
    if params.range not in VALID_RANGES:
        raise HTTPException(
            status_code=400, detail=f"Invalid range. Choose from: {VALID_RANGES}"
        )

    try:
        df = download_market_data_df(params.symbol, period=params.range, interval=params.interval)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No history for {params.symbol}")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty:
        raise HTTPException(status_code=404, detail="No history data after filtering")

    use_unix = params.interval not in {"1d", "5d", "1wk", "1mo", "3mo"}
    bars = []
    for ts, row in df.iterrows():
        t = int(ts.timestamp()) if use_unix else ts.strftime("%Y-%m-%d")
        bars.append({
            "time": t,
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })

    return {
        "symbol": params.symbol.upper(),
        "interval": params.interval,
        "range": params.range,
        "count": len(bars),
        "bars": bars,
    }


@router.get("/search", response_model=SearchResponse)
@limiter.limit(settings.rate_limit_public)
async def search_symbols(request: SearchRequest = Depends(), db: Session = DbDep) -> dict:
    from app.services.broker import get_broker_feed
    symbol = request.q.upper().strip().replace(".NS", "")
    key = get_broker_feed().get_instrument_token(symbol)
    if key:
        return {
            "results": [{"symbol": s + ".NS", "name": request.q, "type": "NSE Equity"}]
        }
    return {"results": []}