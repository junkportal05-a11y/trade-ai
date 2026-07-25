"""Admin router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep
from app.core.security import require_admin
from app.models.schemas import AdminKeyParams
from app.core.worker_health import get_all as get_worker_health

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", response_model=dict)
def admin_health(
    db: Session = DbDep,
    params: AdminKeyParams = Depends(),
) -> dict:
    require_admin(params.x_admin_key)
    from app.db.repositories import repo
    stats = repo.signals.get_stats(db)
    return {"status": "healthy", "signals_stats": stats, "workers": get_worker_health()}


@router.delete("/signals/clear", response_model=dict)
def clear_signals(
    db: Session = DbDep,
    params: AdminKeyParams = Depends(),
) -> dict:
    require_admin(params.x_admin_key)
    from app.db.repositories import repo
    repo.signals.clear_all(db)
    return {"status": "cleared", "message": "All signal history cleared"}
