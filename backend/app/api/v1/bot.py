"""Bot control API endpoints.

POST /api/bot/start  -> set state RUNNING
POST /api/bot/pause  -> set state PAUSED
POST /api/bot/stop   -> set state STOPPED and square off open positions
GET  /api/bot/status -> current state, today P&L, last signal, open positions
GET  /api/bot/trades -> recent live trade log (PENDING/WIN/LOSS/TIMEOUT)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from app.api.deps import SessionDep, OptionalSessionDep, TraderDep, AdminClearanceDep
from app.core.security import CsrfDep
import db
import trading_agent

router = APIRouter(prefix="/api/bot", tags=["bot"])


def _now_ist() -> datetime:
    utc = datetime.now(timezone.utc)
    return utc + timedelta(hours=5, minutes=30)


@router.post("/start")
async def bot_start(request: Request, csrf=CsrfDep, trader=TraderDep) -> Dict[str, Any]:
    """Set bot state to RUNNING. The bot is paper-only; live requests are rejected."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if isinstance(body, dict) and (body.get("paper") is False or body.get("order_mode") == "live"):
        raise HTTPException(
            status_code=400,
            detail="Live trading is disabled. The bot runs in paper mode only.",
        )
    db.set_bot_state("RUNNING")
    return {"status": "ok", "state": db.get_bot_state(), "mode": "paper"}


@router.post("/pause")
async def bot_pause(request: Request, csrf=CsrfDep, trader=TraderDep) -> Dict[str, Any]:
    """Set bot state to PAUSED."""
    db.set_bot_state("PAUSED")
    return {"status": "ok", "state": db.get_bot_state()}


@router.post("/stop")
async def bot_stop(request: Request, csrf=CsrfDep, admin=AdminClearanceDep) -> Dict[str, Any]:
    """Set bot state to STOPPED and square off all open positions."""
    db.set_bot_state("STOPPED")
    try:
        trading_agent._square_off_all(_now_ist())
    except Exception as exc:  # pragma: no cover - best effort square off
        raise HTTPException(status_code=500, detail=f"square off failed: {exc}")
    return {"status": "ok", "state": db.get_bot_state()}


@router.get("/status")
async def bot_status(request: Request, csrf=CsrfDep, trader=TraderDep) -> Dict[str, Any]:
    """Return current state, today's P&L, last signal, and open positions."""
    state = db.get_bot_state()
    today = _now_ist().strftime("%Y-%m-%d")
    todays_pnl = 0.0
    last_signal = None
    positions = []
    try:
        with db._conn() as c:
            row = c.execute(
                "SELECT COALESCE(SUM(pnl_pct),0) AS pnl FROM predictions_history "
                "WHERE status IN ('WIN','LOSS','TIMEOUT') AND resolved_at LIKE ?",
                (today + "%",),
            ).fetchone()
            todays_pnl = float(row["pnl"]) if row else 0.0

            sig = c.execute(
                "SELECT * FROM signals_history ORDER BY scanned_at DESC LIMIT 1"
            ).fetchone()
            last_signal = dict(sig) if sig else None

            pos = c.execute(
                "SELECT * FROM predictions_history WHERE status='PENDING' "
                "ORDER BY prediction_date DESC"
            ).fetchall()
            positions = [dict(p) for p in pos]
    except Exception:
        pass

    return {
        "state": state,
        "today_pnl": round(todays_pnl, 2),
        "last_signal": last_signal,
        "positions": positions,
    }


@router.get("/trades")
async def bot_trades(request: Request, csrf=CsrfDep, session=SessionDep) -> Dict[str, Any]:
    """Return recent live trade log."""
    trades = []
    try:
        with db._conn() as c:
            rows = c.execute(
                "SELECT * FROM predictions_history "
                "WHERE status IN ('PENDING','WIN','LOSS','TIMEOUT') "
                "ORDER BY prediction_date DESC LIMIT 50"
            ).fetchall()
            trades = [dict(r) for r in rows]
    except Exception:
        pass
    return {"trades": trades}