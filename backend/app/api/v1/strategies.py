"""Strategies router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.db.repositories import repo
from app.db.models import Strategy

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("", response_model=list[dict])
def get_strategies(
    active_only: bool = Query(True, description="Filter to only active strategies"),
    db: Session = DbDep,
    _=SessionDep,
) -> list[dict]:
    """Get all strategies."""
    strategies = repo.strategy.get_all(db, active_only=active_only)
    return [s.to_dict() for s in strategies]


@router.get("/{strategy_id}", response_model=dict)
def get_strategy(
    strategy_id: int,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    """Get a specific strategy by ID."""
    strategy = repo.strategy.get(db, strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy with id {strategy_id} not found"
        )
    return strategy.to_dict()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_strategy(
    request: Request,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    """Create a new strategy."""
    # TODO: Implement actual strategy creation from request body
    return {
        "id": 999,
        "name": "New Strategy",
        "description": "Created via API",
        "is_active": True
    }