"""API v1 router aggregator."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, quotes, signals, broker, chat, journal, predictions, backtest, admin, bot, ws, strategies, allocate, tournament

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(quotes.router)
api_router.include_router(signals.router)
api_router.include_router(broker.router)
api_router.include_router(chat.router)
api_router.include_router(journal.router)
api_router.include_router(predictions.router)
api_router.include_router(backtest.router)
api_router.include_router(admin.router)
api_router.include_router(bot.router)
api_router.include_router(ws.router)
api_router.include_router(strategies.router)
api_router.include_router(allocate.router)
api_router.include_router(tournament.router)
