"""API v1 router aggregator — Mono Black & White Redesign v6.1.2
Only includes routes for the 5 active sections: Home, Charts, Scanner, Predictions, Strategies.
Per §4: removed bot.py, allocate.py, tournament.py, broker/chat/ws/admin routes.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import predictions, strategies, backtest, signals, quotes

api_router = APIRouter()
api_router.include_router(predictions.router)
api_router.include_router(strategies.router)
api_router.include_router(backtest.router)
api_router.include_router(signals.router)
api_router.include_router(quotes.router)