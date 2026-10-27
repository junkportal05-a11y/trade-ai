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
    fallback: bool = False


class SearchResponse(BaseModel):
    results: list[dict[str, str]]


class ScanRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"])
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
    gates: dict[str, int] = Field(default_factory=dict)
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
    confidence: float | None = None
    reasoning: str | None = None


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
    prediction_type: str = Field(..., pattern=r"^(BULLISH|BEARISH|UP|DOWN)$")

    @field_validator("prediction_type", mode="before")
    @classmethod
    def normalize_prediction_type(cls, v: Any) -> str:
        if isinstance(v, str):
            val = v.upper().strip()
            if val in ("UP", "BULLISH", "LONG"):
                return "BULLISH"
            if val in ("DOWN", "BEARISH", "SHORT"):
                return "BEARISH"
        return v
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
    exit_price: float = Field(..., gt=0)
    manual_override_reason: str = Field(..., min_length=1, max_length=500)
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
    symbol: str = Field(..., min_length=1, max_length=50)
    interval: str = Field(..., min_length=1, max_length=20)
    range: str = Field(..., min_length=1, max_length=20)


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
    symbol: str = Field(default="RELIANCE.NS")
    start_date: str = Field(default="2024-01-01")
    end_date: str = Field(default="2024-12-31")
    strategy: str | None = Field(
        default="intraday_momentum",
        description="Informational only. The engine runs one daily trend strategy.",
    )
    capital: float | None = Field(default=100000.0)
    risk_pct: float = Field(
        default=0.02,
        description="Fraction of capital risked per trade (0.02 = 2%). Percent-style values >1 are divided by 100.",
    )
    stop_atr: float = Field(default=1.5)
    target_atr: float = Field(default=2.5)
    initial_capital: float = Field(default=100000.0)
    entry_score: int = Field(default=5, ge=-10, le=10)
    adx_min: float = Field(default=0.0, ge=0)
    early_exit: int = Field(default=-4, description="Daily score at or below which an open trade exits.")

    @field_validator("symbol", mode="before")
    @classmethod
    def sanitize_symbol(cls, v: Any) -> str:
        if not v or not isinstance(v, str):
            return "RELIANCE.NS"
        s = v.strip().upper()
        if not s.endswith(".NS") and "^" not in s and "." not in s:
            s += ".NS"
        return s

    @field_validator("capital", "initial_capital", mode="before")
    @classmethod
    def sanitize_capital(cls, v: Any) -> float:
        try:
            val = float(v)
            return abs(val) if val != 0 else 100000.0
        except Exception:
            return 100000.0

    @field_validator("risk_pct", mode="before")
    @classmethod
    def sanitize_risk_pct(cls, v: Any) -> float:
        try:
            val = abs(float(v))
        except Exception:
            return 0.02
        if val == 0:
            return 0.02
        return val / 100.0 if val > 1.0 else val

    @field_validator("stop_atr", mode="before")
    @classmethod
    def sanitize_stop_atr(cls, v: Any) -> float:
        try:
            val = abs(float(v))
            return val if val != 0 else 1.5
        except Exception:
            return 1.5

    @field_validator("target_atr", mode="before")
    @classmethod
    def sanitize_target_atr(cls, v: Any) -> float:
        try:
            val = abs(float(v))
            return val if val != 0 else 2.5
        except Exception:
            return 2.5

    @field_validator("entry_score", "early_exit", mode="before")
    @classmethod
    def sanitize_score(cls, v: Any) -> int:
        if isinstance(v, bool):
            return -4 if v else -999
        try:
            return int(v)
        except Exception:
            return -4


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z][A-Z0-9.]*$")


class QuoteRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9]+(?:\.[A-Z0-9]+)?$")


class ChartAnalysisRequest(BaseModel):
    """Request schema for chart analysis endpoint."""
    image_base64: str = Field(..., description="Base64 encoded PNG/JPEG image")
    symbol: str = Field(default="", description="Optional symbol for context")


class ChartAnalysisResponse(BaseModel):
    """Response schema for chart analysis."""
    trend: str
    support_levels: list[float]
    resistance_levels: list[float]
    patterns: list[str]
    breakout_signal: str | None
    confidence: float
    notes: str
    source: str
