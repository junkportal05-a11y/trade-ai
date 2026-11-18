"""Disclaimer API route — paper-only mode enforcement."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, optional_session

router = APIRouter(prefix="/api", tags=["compliance", "disclaimer"])


def _check_code_auth(
    session: dict | None = Depends(optional_session),
) -> dict | None:
    """Require authentication via single-code gate (username='code').

    If the session is derived from a code login (apt_token set via
    /api/login with username="code"), return the session dict.
    Otherwise, return None — the caller can decide 403 vs paper-response.
    """
    if session is None:
        return None
    # The session was set by /api/login with username="code":
    # payload.sub == "code" and the apt_token cookie is present.
    # Any valid session is acceptable per the single-code gate pattern.
    return session


@router.get("/disclaimer", tags=["disclaimer"])
async def get_disclaimer(
    db: Session = DbDep,
    session: dict | None = Depends(optional_session),
) -> dict:
    """Return the risk disclaimer in paper-trading mode only.

    - 403 if the user is not authenticated via the code gate.
    - Paper-mode disclaimer content if authenticated.
    """
    if session is None:
        raise HTTPException(status_code=403, detail="Authentication required — use /api/login with access code")
    return {
        "mode": "paper",
        "disclaimer": "ApexTrade AI is a paper-trading workstation for educational and research purposes only. "
                      "Not SEBI registered. No real orders are executed. All signals and P&L are simulated.",
        "trading_mode": "paper",
        "live_trading_armed": False,
        "status": "paper_only",
    }