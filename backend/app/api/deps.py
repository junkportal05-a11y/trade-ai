"""FastAPI dependencies — DB session, auth, rate limiting."""
from __future__ import annotations

import hashlib
from typing import Any

from fastapi import Depends, Request

from app.core.database import get_db
from app.core.security import require_session, optional_session, require_admin, require_clearance


# ── Database dependency ─────────────────────────────────────────────────────
DbDep = Depends(get_db)


# ── Auth dependency ─────────────────────────────────────────────────────────
SessionDep = Depends(require_session)
OptionalSessionDep = Depends(optional_session)
AdminDep = Depends(require_admin)
TraderDep = Depends(require_clearance("LEVEL_2_TRADER"))
AdminClearanceDep = Depends(require_clearance("LEVEL_3_ADMIN"))


from app.core.limiter import get_real_client_ip


# ── Rate limit key extractor ────────────────────────────────────────────────
def get_user_or_ip(request: Request) -> str:
    token = request.headers.get("x-session-token")
    if token:
        return f"user:{hashlib.sha256(token.encode()).hexdigest()}"
    return get_real_client_ip(request)


# ── Context builder for chat ─────────────────────────────────────────────────
async def get_chat_context(request: Request) -> dict[str, Any]:
    """Build context from request for AI chat."""
    body = await request.json() if request.method in ("POST", "PUT", "PATCH") else {}
    ctx = body.get("context", {})
    return ctx
