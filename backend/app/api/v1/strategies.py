"""Strategies router."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request, status

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

# Mock strategies until DB model is implemented
MOCK_STRATEGIES = [
    {
        "id": 1,
        "name": "Moving Average Crossover",
        "description": "Simple EMA crossover strategy",
        "is_active": True
    },
    {
        "id": 2,
        "name": "Mean Reversion",
        "description": "RSI based mean reversion",
        "is_active": True
    }
]

@router.get("", response_model=list[dict])
def get_strategies(
    active_only: bool = Query(True, description="Filter to only active strategies"),
) -> list[dict]:
    """Get all strategies."""
    if active_only:
        return [s for s in MOCK_STRATEGIES if s["is_active"]]
    return MOCK_STRATEGIES


@router.get("/{strategy_id}", response_model=dict)
def get_strategy(strategy_id: int) -> dict:
    """Get a specific strategy by ID."""
    for s in MOCK_STRATEGIES:
        if s["id"] == strategy_id:
            return s
    return MOCK_STRATEGIES[0]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_strategy(request: Request) -> dict:
    """Create a new strategy."""
    return {
        "id": 999,
        "name": "New Strategy",
        "description": "Created from UI",
        "is_active": True,
    }