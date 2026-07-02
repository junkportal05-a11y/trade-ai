"""Predictions router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import PredictionCreate
from app.db.repositories import repo

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
