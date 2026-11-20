"""Terms of Service API route — paper-only mode enforcement."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, optional_session

router = APIRouter(prefix="/api", tags=["compliance", "terms"])


@router.get("/terms", tags=["terms"])
async def get_terms(
    db: Session = DbDep,
    session: dict | None = Depends(optional_session),
) -> dict:
    """Return the Terms of Service in paper-trading mode only.

    - 403 if the user is not authenticated via the code gate.
    - Paper-mode terms content if authenticated.
    """
    if session is None:
        raise HTTPException(status_code=403, detail="Authentication required — use /api/login with access code")
    return {
        "mode": "paper",
        "terms": "ApexTrade operates in paper trading mode by default. No real orders are sent to any broker or exchange. "
                 "Live trading is not available in this personal workstation build; the bot runs in paper mode only. "
                 "Governing law: India, exclusive jurisdiction Mumbai courts.",
        "trading_mode": "paper",
        "live_trading_armed": False,
        "status": "paper_only",
    }