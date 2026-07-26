"""Predictions router."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import not_
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import PredictionCreate, PredictionResolveRequest
from app.db.repositories import repo
from app.db.models import PredictionsHistory

router = APIRouter(prefix="/api", tags=["predictions"])


@router.get("/predictions", response_model=list[dict])
def get_predictions(db: Session = DbDep, _=SessionDep) -> list[dict]:
    return repo.predictions.get_all(db)


@router.get("/predictions/pending", response_model=list[dict])
def get_pending_predictions(db: Session = DbDep, _=SessionDep) -> list[dict]:
    return repo.predictions.get_pending(db)


@router.post("/predictions", response_model=dict)
def create_prediction(
    pred: PredictionCreate,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    pred_id = repo.predictions.add(db, pred.model_dump())
    return {"id": pred_id, "status": "created"}


@router.get("/predictions/stats", response_model=dict)
def get_prediction_stats(db: Session = DbDep, _=SessionDep) -> dict:
    """
    Returns aggregate statistics over all *resolved* predictions.
    - win_rate: percentage of resolved predictions with positive PnL
    - avg_error: average absolute percent error of resolved predictions
    - resolved_predictions: total number of resolved predictions
    """
    # Grab all resolved predictions that are not still pending
    resolved = (
        db.query(PredictionsHistory)
        .filter(
            PredictionsHistory.status != "PENDING",
            PredictionsHistory.resolved_at.is_not(None),
        )
        .all()
    )
    n = len(resolved)
    if n == 0:
        return {"win_rate": 0.0, "avg_error": 0.0, "resolved_predictions": 0}

    wins = sum(1 for r in resolved if (r.pnl_pct or 0) > 0)
    # Compute average error only on rows that actually have the needed fields
    errors = [
        abs((r.actual_outcome - r.target_price) / r.target_price) * 100
        for r in resolved
        if r.actual_outcome is not None and r.target_price and r.target_price != 0
    ]

    return {
        "win_rate": round(wins / n * 100, 1),
        "avg_error": round(sum(errors) / len(errors), 2) if errors else 0.0,
        "resolved_predictions": n,
    }

@router.post("/predictions/{prediction_id}/resolve", response_model=dict)
def resolve_prediction(
    prediction_id: int,
    req: PredictionResolveRequest,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    pred = db.query(PredictionsHistory).filter(PredictionsHistory.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    exit_price = req.exit_price or (pred.target_price if req.actual_outcome == "TARGET_HIT" else pred.stop_loss)
    
    # Calculate PnL percentage
    if pred.entry_price and pred.entry_price > 0:
        if pred.prediction_type == "BULLISH":
            pnl_pct = ((exit_price - pred.entry_price) / pred.entry_price) * 100.0
        else:
            pnl_pct = ((pred.entry_price - exit_price) / pred.entry_price) * 100.0
    else:
        pnl_pct = 0.0

    pred.status = "RESOLVED"
    pred.actual_outcome = req.actual_outcome
    pred.pnl_pct = round(pnl_pct, 2)
    pred.resolved_at = datetime.now(timezone.utc).isoformat()

    db.commit()
    db.refresh(pred)

    return {
        "id": pred.id,
        "status": pred.status,
        "actual_outcome": pred.actual_outcome,
        "pnl_pct": pred.pnl_pct,
        "resolved_at": pred.resolved_at,
    }
