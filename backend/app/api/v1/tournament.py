"""
backend/app/api/v1/tournament.py — FastAPI Router for 30-Strategy Quant Tournament
"""
import os
import json
from fastapi import APIRouter, Request, HTTPException
from app.api.deps import SessionDep
from app.core.security import CsrfDep
from app.core.limiter import limiter
from strategy_tournament import run_full_tournament
from bot_trainer import train_and_export_weights, WEIGHTS_FILE

router = APIRouter(prefix="/api/backtest/tournament", tags=["tournament"])

@router.post("", response_model=dict)
@limiter.limit("5/minute")
async def run_tournament(request: Request, csrf=CsrfDep, _=SessionDep) -> dict:
    """Run full 30-strategy quant tournament across local 10y datasets."""
    data = train_and_export_weights()
    if not data:
        raise HTTPException(status_code=500, detail="Failed executing tournament")
    return {"status": "success", "data": data}

@router.get("/leaderboard", response_model=dict)
def get_leaderboard(_=SessionDep) -> dict:
    """Fetch current 30-strategy leaderboard and ensemble weights."""
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, "r") as f:
                data = json.load(f)
            return {"status": "success", "data": data}
        except Exception:
            pass
    # If weights not cached yet, run trainer
    data = train_and_export_weights()
    return {"status": "success", "data": data}
