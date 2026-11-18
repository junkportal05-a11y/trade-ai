"""Signal scanning router."""
from __future__ import annotations

import asyncio
import functools
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import CsrfDep
from app.api.deps import DbDep, SessionDep
from app.models.schemas import ScanRequest, SignalResponse, SignalsQuery
from app.core.executors import scan_executor
from app.core.logging import logger
from app.services.telegram_bot import telegram_bot

router = APIRouter(prefix="/api", tags=["signals"])

SIGNAL_SCAN_TIMEOUT_SECONDS = 85


def _unavailable_payload(
    *,
    gates: dict,
    market: str,
    typ: str,
    error: str | None,
    message: str,
) -> dict:
    """Honest empty scan response — status unavailable, nothing invented."""
    return {
        "market": market,
        "type": typ,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total": 0,
        "signals": [],
        "gates": gates,
        "disclaimer": "Algorithmic signals only — not financial advice.",
        "status": "unavailable",
        "error": error,
        "message": message,
        "symbols_scanned": 0,
    }


def _success_payload(*, results: list, gates: dict, market: str, typ: str, limit: int | None = None) -> dict:
    """Successful scan payload with honest status/symbols_scanned derivatives."""
    scanned = len({r.get("symbol") for r in results if r.get("symbol")})
    payload = {
        "market": market,
        "type": typ,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "signals": results if limit is None else results[:limit],
        "gates": gates,
        "disclaimer": "Algorithmic signals only — not financial advice.",
        "status": "ok" if results else "unavailable",
        "error": None,
        "message": None if results else (
            "Scan ran but produced no qualifying setups or scannable data — "
            "nothing is being made up. Tap RETRY shortly."
        ),
        "symbols_scanned": scanned,
    }
    return payload


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

    gates: dict = {}
    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(
                scan_executor,
                functools.partial(run_scan, watchlist, gate_log=gates),
            ),
            timeout=SIGNAL_SCAN_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("[signals] scan timed out after %ss", SIGNAL_SCAN_TIMEOUT_SECONDS)
        return _unavailable_payload(
            gates=gates, market="NSE", typ="intraday",
            error=f"Scan took longer than {SIGNAL_SCAN_TIMEOUT_SECONDS}s (backend cold start)",
            message="First scan on free tier takes 2 min. Try again in 30s.",
        )
    except Exception as exc:
        logger.warning("[signals] scan crashed: %s", exc)
        return _unavailable_payload(
            gates=gates, market="NSE", typ="intraday",
            error=f"{type(exc).__name__}: {exc}",
            message="The scan engine failed mid-run — selecting no results rather than partial data. Tap RETRY shortly.",
        )

    return _success_payload(results=results, gates=gates, market="NSE", typ="intraday", limit=params.limit)


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

    gates: dict = {}
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
                    gate_log=gates,
                ),
            ),
            timeout=SIGNAL_SCAN_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("[signals] POST scan timed out after %ss", SIGNAL_SCAN_TIMEOUT_SECONDS)
        return _unavailable_payload(
            gates=gates, market=req.market_segment, typ=req.interval,
            error=f"Scan took longer than {SIGNAL_SCAN_TIMEOUT_SECONDS}s",
            message="Try again in 30s when backend is warm.",
        )
    except Exception as exc:
        logger.warning("[signals] POST scan crashed: %s", exc)
        return _unavailable_payload(
            gates=gates, market=req.market_segment, typ=req.interval,
            error=f"{type(exc).__name__}: {exc}",
            message="The scan engine failed mid-run — selecting no results rather than partial data. Tap RETRY shortly.",
        )

    # Send Telegram alerts for high-confidence signals
    if results and settings.telegram_bot_token and settings.telegram_chat_id:
        min_conf = getattr(settings, 'telegram_min_confidence', 75)
        for sig in results:
            if sig.get('confidence', 0) >= min_conf:
                try:
                    telegram_bot.send_signal_alert(sig)
                except Exception as te:
                    logger.warning(f"Failed to send Telegram alert: {te}")

    return _success_payload(results=results, gates=gates, market=req.market_segment, typ=req.interval)


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