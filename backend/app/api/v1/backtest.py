"""Backtest router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep

router = APIRouter(prefix="/api", tags=["backtest"])


@router.post("/backtest", response_model=dict)
def run_backtest(
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    # Delegates to existing backtest engine
    from app.services.backtest import run_backtest as _run
    return _run()
