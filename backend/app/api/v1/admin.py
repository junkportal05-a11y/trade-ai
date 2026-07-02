"""Admin router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep
from app.core.security import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", response_model=dict)
def admin_health(
    db: Session = DbDep,
    x_admin_key: str | None = None,
) -> dict:
    require_admin(x_admin_key)
    from app.db.repositories import repo
    stats = repo.signals.get_stats(db)
    return {"status": "healthy", "signals_stats": stats}


@router.delete("/signals/clear", response_model=dict)
def clear_signals(
    db: Session = DbDep,
    x_admin_key: str | None = None,
) -> dict:
    require_admin(x_admin_key)
    from app.db.repositories import repo
    repo.signals.clear_all(db)
    return {"status": "cleared", "message": "All signal history cleared"}
