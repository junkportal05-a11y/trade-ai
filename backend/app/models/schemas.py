"""Pydantic schemas for API request/response validation."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import VALID_INTERVALS, VALID_RANGES


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    clearance: str
    expires_in: int


class StatusResponse(BaseModel):
    status: str
    message: str


class QuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float | None = None
    change_percent: float | None = None
    volume: int | None = None


class HistoryRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z][A-Z0-9.]*$")
    interval: str = Field(..., pattern=r"^(1m|2m|5m|15m|30m|60m|1h|1d|5d|1wk|1mo|3mo|6mo|1y|2y|5y|max)$")
    range: str = Field(..., pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$")


class CandleBar(BaseModel):
    time: int | str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoryResponse(BaseModel):
    symbol: str
    interval: str
    range: str
    count: int
    bars: list[CandleBar]


class SearchResponse(BaseModel):
    results: list[dict[str, str]]


class ScanRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=50)
    interval: str = Field(default="15m", pattern=r"^(1m|5m|15m|30m|1h|1d|1wk|1mo)$")
    capital: float = Field(default=100_000.0, gt=0)
    trading_style: str = Field(default="Intraday Momentum")
    risk_level: str = Field(default="Medium")
    market_segment: str = Field(default="NSE")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        return [s.strip().upper() for s in v if s.strip()]


class SignalResponse(BaseModel):
    market: str
    type: str
    scan_time: str
    total: int
    signals: list[dict[str, Any]]
    disclaimer: str


class SingleSignalResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    signal: str
    confidence: int
    entry: float
    target: float
    stop_loss: float
    rr_ratio: float
    atr: float
    reasoning: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(..., min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    context: dict[str, Any] | None = None
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    reply: str
    source: Literal["gemini", "heuristic"]


class AngelOneCredentials(BaseModel):
    api_key: str = Field(..., min_length=1)
    client_code: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=4, max_length=12)
    totp_secret: str = Field(..., min_length=1)


class AngelOneStatusResponse(BaseModel):
    connected: bool
    client_code: str
    credentials_saved: bool = False


class JournalEntry(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    direction: str = Field(..., pattern=r"^(BUY|SELL|LONG|SHORT)$")
    entry_price: float = Field(..., gt=0)
    exit_price: float | None = None
    qty: int = Field(..., gt=0)
    entry_date: str | None = None
    reason: str | None = None
    emotion: str | None = Field(default="Calm", max_length=50)
    status: str = Field(default="OPEN", pattern=r"^(OPEN|CLOSED)$")
    pnl: float | None = None


class JournalEntryResponse(JournalEntry):
    id: int


class PredictionCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    prediction_type: str = Field(..., pattern=r"^(BULLISH|BEARISH)$")
    entry_price: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    confidence_score: int = Field(..., ge=0, le=100)
    rsi: float | None = None
    macd: float | None = None
    adx: float | None = None
    sector: str | None = None
    market_cap: float | None = None
    volume_ratio: float | None = None
    vwap_distance: float | None = None
    atr: float | None = None
    news_score: float | None = None
    market_breadth: float | None = None
    sector_strength: float | None = None
    nifty_trend: str | None = None
    market_regime_snapshot: str | None = Field(default="UNKNOWN")
    risk_amount: float | None = None
    confidence_probability: float | None = Field(default=0.5, ge=0.0, le=1.0)
    regime_score: float | None = None
    sector_score: float | None = None
    volume_score: float | None = None
    rs_score: float | None = None
    trade_quality_score: float | None = None
    correlation_score: float | None = None


class PredictionResolveRequest(BaseModel):
    actual_outcome: str = Field(..., pattern=r"^(TARGET_HIT|STOP_HIT|EXPIRED|MANUAL_EXIT)$")
    exit_price: float | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=500)


class KeepAliveResponse(BaseModel):
    status: str
    message: str
    current_time_ist: str
    market_status: str


class DashboardMetrics(BaseModel):
    total: int
    pending: int
    won: int
    lost: int
    expired: int
    closed: int
    resolved: int
    win_rate: float
    avg_pnl: float
    profit_factor: float
    ev_pct: float
    max_drawdown: float
    avg_r: float
    by_sector: list[dict]
    by_direction: list[dict]
    leaderboard: list[dict]


class OrderRequest(BaseModel):
    side: str = Field(..., pattern=r"^(BUY|SELL)$")
    symbol: str = Field(..., min_length=1, max_length=50)
    type: str = Field(default="market", pattern=r"^(market|limit)$")
    qty: int = Field(..., gt=0, le=100_000)
    limit_price: float | None = Field(default=None, gt=0)

    @field_validator("limit_price")
    @classmethod
    def validate_limit(cls, v: float | None, info) -> float | None:
        if info.data.get("type") == "limit" and v is None:
            raise ValueError("limit_price is required for limit orders")
        return v


class PriceAlert(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50)
    condition: str = Field(..., pattern=r"^(above|below)$")
    target_price: float = Field(..., gt=0)


class HistoryParams(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z][A-Z0-9.]*$")
    interval: str = Field(..., pattern=r"^(1m|2m|5m|15m|30m|60m|1h|1d|5d|1wk|1mo|3mo|6mo|1y|2y|5y|max)$")
    range: str = Field(..., pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$")


class SignalsQuery(BaseModel):
    symbols: str | None = Field(default=None, min_length=1, max_length=200)
    limit: int = Field(default=20, ge=1, le=50)

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v):
        if v is None:
            return None
        cleaned = [s.strip().upper() for s in v.split(",") if s.strip()]
        if not cleaned:
            raise ValueError("symbols must contain at least one non-empty symbol")
        sym_regex = re.compile(r"^[A-Z0-9.]+$")
        for s in cleaned:
            if not sym_regex.fullmatch(s):
                raise ValueError(f"Invalid symbol format: {s}")
        return ",".join(cleaned)


class AdminKeyParams(BaseModel):
    x_admin_key: str | None = Field(default=None, min_length=1)


class BacktestRequest(BaseModel):
    symbol: str = Field(..., pattern=r"^[A-Z][A-Z0-9.]*$")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    strategy: str | None = Field(default="intraday_momentum")
    capital: float | None = Field(default=100000.0, gt=0)
    risk_pct: float = Field(default=2.0, gt=0)
    stop_atr: float = Field(default=1.5, gt=0)
    target_atr: float = Field(default=2.0, gt=0)
    initial_capital: float = Field(default=100000.0, gt=0)
    entry_score: int = Field(default=60, ge=0)
    adx_min: float = Field(default=20.0, ge=0)
    early_exit: bool = Field(default=True)


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z][A-Z0-9.]*$")


class QuoteRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9]+(?:\.[A-Z0-9]+)?$")
