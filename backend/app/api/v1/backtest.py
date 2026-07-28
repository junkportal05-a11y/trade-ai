"""Backtest router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep, OptionalSessionDep

router = APIRouter(prefix="/api", tags=["backtest"])


from app.models.schemas import BacktestRequest


@router.post("/backtest/run", response_model=dict)
@router.post("/backtest", response_model=dict)
def run_backtest_route(
    req: BacktestRequest | None = None,
    db: Session = DbDep,
    _=OptionalSessionDep,
) -> dict:
    from app.services.backtest import run_backtest as _run
    return _run()
