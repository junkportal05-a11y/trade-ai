"""Quotes, history, and market data router."""
from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep
from app.models.schemas import HistoryResponse, QuoteResponse, SearchResponse
from app.core.constants import VALID_INTERVALS, VALID_RANGES

router = APIRouter(prefix="/api", tags=["quotes"])


@router.get("/", response_model=dict)
def root() -> dict:
    return {"status": "ok", "message": "Trading Platform API is running"}


@router.get("/keepalive", response_model=dict)
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
def get_quote(
    symbol: str = Query(..., min_length=1, max_length=50),
    db: Session = DbDep,
) -> dict:
    from app.services.quotes import get_symbol_quote

    result = get_symbol_quote(symbol)
    if not result:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    return result


@router.get("/history", response_model=HistoryResponse)
def get_history(
    symbol: str = Query(..., min_length=1, max_length=50),
    interval: str = Query("1d", description="Bar interval"),
    range: str = Query("3mo", description="Date range"),
    db: Session = DbDep,
) -> dict:
    from app.services.market_data import download_market_data_df

    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400, detail=f"Invalid interval. Choose from: {VALID_INTERVALS}"
        )
    if range not in VALID_RANGES:
        raise HTTPException(
            status_code=400, detail=f"Invalid range. Choose from: {VALID_RANGES}"
        )

    try:
        df = download_market_data_df(symbol, period=range, interval=interval)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No history for {symbol}")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty:
        raise HTTPException(status_code=404, detail="No history data after filtering")

    use_unix = interval not in {"1d", "5d", "1wk", "1mo", "3mo"}
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
        "symbol": symbol.upper(),
        "interval": interval,
        "range": range,
        "count": len(bars),
        "bars": bars,
    }


@router.get("/search", response_model=SearchResponse)
def search_symbols(
    q: str = Query(..., min_length=1, max_length=50),
    db: Session = DbDep,
) -> dict:
    from app.services.broker import get_broker_feed

    symbol = q.upper().strip().replace(".NS", "")
    key = get_broker_feed().get_instrument_token(symbol)
    if key:
        return {"results": [{"symbol": symbol + ".NS", "name": symbol, "type": "NSE Equity"}]}
    return {"results": []}
