"""FastAPI dependencies — DB session, auth, rate limiting."""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_session, optional_session, get_token_from_request, decode_access_token
from app.core.config import settings
from app.db.repositories import repo


# ── Database dependency ─────────────────────────────────────────────────────
DbDep = Depends(get_db)


# ── Auth dependency ─────────────────────────────────────────────────────────
SessionDep = Depends(require_session)
OptionalSessionDep = Depends(optional_session)


# ── Rate limit key extractor ────────────────────────────────────────────────
def get_user_or_ip(request: Request) -> str:
    token = request.headers.get("x-session-token")
    if token:
        return f"user:{token}"
    return str(request.client.host) if request.client else "unknown"


# ── Context builder for chat ─────────────────────────────────────────────────
async def get_chat_context(request: Request) -> dict[str, Any]:
    """Build context from request for AI chat."""
    body = await request.json() if request.method in ("POST", "PUT", "PATCH") else {}
    ctx = body.get("context", {})
    return ctx
