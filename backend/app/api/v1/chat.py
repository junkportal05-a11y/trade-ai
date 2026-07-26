"""AI Chat router."""
from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import ChatRequest, ChatResponse
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_user)
async def chat(
    req: ChatRequest,
    request: Request,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.chat import get_chat_reply

    symbol = (req.context or {}).get("symbol", "the market")
    price = (req.context or {}).get("price")
    chg_pct = (req.context or {}).get("changePct")

    return get_chat_reply(req, symbol, price, chg_pct)