"""Backtest router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.core.security import CsrfDep
from app.models.schemas import BacktestRequest

router = APIRouter(prefix="/api", tags=["backtest"])


@router.post("/backtest/run", response_model=dict)
@router.post("/backtest", response_model=dict)
async def run_backtest_route(
    request: Request,
    req: BacktestRequest | None = None,
    db: Session = DbDep,
    csrf=CsrfDep,
    _=SessionDep,
) -> dict:
    from app.main import run_backtest as _run_main_backtest
    if req is None:
        try:
            body = await request.json()
            req = BacktestRequest.model_validate(body)
        except Exception:
            req = BacktestRequest(symbol="RELIANCE.NS", start_date="2024-01-01", end_date="2024-12-31")
    return await _run_main_backtest(request, req)
