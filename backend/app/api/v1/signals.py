"""Signal scanning router."""
from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import CsrfDep
from app.api.deps import DbDep, OptionalSessionDep, SessionDep
from app.models.schemas import ScanRequest, SignalResponse, SignalsQuery
from app.core.config import settings
from app.core.executors import scan_executor

router = APIRouter(prefix="/api", tags=["signals"])


@router.get("/signals", response_model=SignalResponse)
async def get_signals(
    request: Request,
    params: SignalsQuery = Depends(),
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.signal_engine import NSE_WATCHLIST, run_scan

    loop = asyncio.get_event_loop()

    if params.symbols:
        sym_list = [s.strip().upper() for s in params.symbols.split(",") if s.strip()]
        wl_map = {w["symbol"]: w for w in NSE_WATCHLIST}
        watchlist = [
            wl_map.get(s, {"symbol": s, "name": s.replace(".NS", ""), "sector": "NSE"})
            for s in sym_list
        ]
    else:
        watchlist = NSE_WATCHLIST

    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(
                scan_executor,
                functools.partial(run_scan, watchlist),
            ),
            timeout=85,
        )
    except asyncio.TimeoutError:
        return {
            "error": "Scan took too long (backend cold start)",
            "total": 0,
            "signals": [],
            "message": "First scan on free tier takes 2 min. Try again in 30s.",
            "market": "NSE",
            "type": "intraday",
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Algorithmic signals only — not financial advice.",
        }

    return {
        "market": "NSE",
        "type": "intraday",
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "signals": results[: params.limit],
        "disclaimer": "Algorithmic signals only — not financial advice.",
    }


@router.post("/scan", response_model=SignalResponse)
async def post_scan(
    req: ScanRequest,
    request: Request,
    db: Session = DbDep,
    csrf=CsrfDep,
    _=SessionDep,
) -> dict:
    from app.services.signal_engine import NSE_WATCHLIST, run_scan

    loop = asyncio.get_event_loop()
    wl_map = {w["symbol"]: w for w in NSE_WATCHLIST}
    watchlist = [
        wl_map.get(s.upper(), {"symbol": s.upper(), "name": s.upper().replace(".NS", ""), "sector": "NSE"})
        for s in req.symbols
    ]

    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(
                scan_executor,
                functools.partial(
                    run_scan,
                    watchlist,
                    req.interval,
                    req.trading_style,
                    req.risk_level,
                    req.market_segment,
                    req.capital,
                ),
            ),
            timeout=85,
        )
    except asyncio.TimeoutError:
        return {
            "error": "Scan took too long",
            "total": 0,
            "signals": [],
            "message": "Try again in 30s when backend is warm.",
            "market": "NSE",
            "type": "intraday",
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Algorithmic signals only — not financial advice.",
        }

    return {
        "market": "NSE",
        "type": "intraday",
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "signals": results,
        "disclaimer": "Algorithmic signals only — not financial advice.",
    }


@router.get("/signal/{symbol}", response_model=dict)
async def get_signal_single(
    symbol: str,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.signal_engine import NSE_WATCHLIST, analyse_symbol

    sym = symbol.upper()
    if not sym.endswith(".NS"):
        sym = sym + ".NS"

    wl_map = {w["symbol"]: w for w in NSE_WATCHLIST}
    meta = wl_map.get(sym, {"symbol": sym, "name": sym.replace(".NS", ""), "sector": "NSE"})

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        scan_executor,
        lambda: analyse_symbol(meta["symbol"], meta["name"], meta["sector"]),
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch data for {sym}. Market may be closed or symbol invalid.",
        )
    return result


@router.get("/data/confidence", response_model=dict)
def get_data_confidence(
    symbols: str | None = Query(default=None),
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    """
    Returns the latest measured data-quality score. When no check has been
    recorded, confidence is reported as unknown instead of a fabricated value.
    """
    from app.db.repositories import repo

    now = datetime.now(timezone.utc)
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else ["RELIANCE.NS", "TCS.NS", "NIFTY"]
    latest = repo.data_quality.get_latest(db)

    confidence = latest.get("confidence_score") if latest else None
    checked_at = latest.get("checked_at") if latest else None
    freshness = "MEASURED" if latest else "UNKNOWN"
    source = "DATA_QUALITY_CHECK" if latest else "NOT_MEASURED"
    locked = bool(latest.get("locked")) if latest else False

    scores = []
    for s in sym_list:
        scores.append({
            "symbol": s,
            "confidence_score": None,
            "freshness_status": freshness,
            "last_updated": checked_at,
            "data_source": source,
            "latency_ms": None,
            "note": "Global data-quality score; per-symbol freshness is not measured.",
        })

    return {
        "market": "NSE",
        "overall_confidence": confidence,
        "confidence_measured": latest is not None,
        "freshness_status": freshness,
        "data_source": source,
        "locked": locked,
        "symbols_evaluated": len(scores),
        "scores": scores,
        "timestamp": now.isoformat(),
    }