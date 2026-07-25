"""Predictions router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import not_
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import PredictionCreate
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
