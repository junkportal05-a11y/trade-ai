"""Privacy Policy API route — paper-only mode enforcement."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, optional_session

router = APIRouter(prefix="/api", tags=["compliance", "privacy"])


@router.get("/privacy", tags=["privacy"])
async def get_privacy(
    db: Session = DbDep,
    session: dict | None = Depends(optional_session),
) -> dict:
    """Return the Privacy Policy in paper-trading mode only.

    - 403 if the user is not authenticated via the code gate.
    - Paper-mode privacy content if authenticated.
    """
    if session is None:
        raise HTTPException(status_code=403, detail="Authentication required — use /api/login with access code")
    return {
        "mode": "paper",
        "privacy": "ApexTrade is a local-first, personal workstation. We collect minimal data: access code (hashed with bcrypt), "
                   "session token (JWT stored in httpOnly, secure, sameSite=None cookie + localStorage mirror), "
                   "local preferences (API URL, chart settings, watchlist favorites in localStorage), "
                   "trading data (paper trades, signals, predictions, journal entries in local SQLite), "
                   "market data cache (OHLCV bars in memory). We do not collect: personal identification, payment info, "
                   "browsing history, location, or device fingerprinting. The Platform is not intended for users under 18.",
        "trading_mode": "paper",
        "live_trading_armed": False,
        "status": "paper_only",
    }