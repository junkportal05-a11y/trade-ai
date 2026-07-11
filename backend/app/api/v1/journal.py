"""Trade journal router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import JournalEntry, JournalEntryResponse
from app.db.repositories import repo

router = APIRouter(prefix="/api", tags=["journal"])


@router.get("/journal", response_model=list[dict])
def get_journal(db: Session = DbDep, _=SessionDep) -> list[dict]:
    return repo.journal.get_all(db)


@router.post("/journal", response_model=JournalEntryResponse)
def add_journal(
    entry: JournalEntry,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    entry_id = repo.journal.add(db, entry.model_dump())
    return {"id": entry_id, **entry.model_dump()}


@router.delete("/journal/{entry_id}", response_model=dict)
def delete_journal(
    entry_id: int,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    deleted = repo.journal.delete(db, entry_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return {"status": "deleted", "id": entry_id}
