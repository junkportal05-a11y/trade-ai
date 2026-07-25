"""SQLAlchemy ORM models for all database tables."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import relationship, declarative_base

from app.core.database import Base


class SignalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    HIT_TARGET = "HIT_TARGET"
    HIT_STOP = "HIT_STOP"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class PredictionStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    HIT_TARGET = "HIT_TARGET"
    HIT_STOP = "HIT_STOP"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class ScanTypeEnum(str, enum.Enum):
    INTRADAY = "INTRADAY"
    OVERNIGHT = "OVERNIGHT"


class TradeDirectionEnum(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"
    SHORT = "SHORT"


class SignalHistory(Base):
    __tablename__ = "signals_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=False)
    signal_type = Column(String(20), nullable=False)
    confidence = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    rr_ratio = Column(Float, default=0.0)
    atr = Column(Float, default=0.0)
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    scan_type = Column(String(20), default="INTRADAY")
    status = Column(String(20), default="PENDING")
    exit_price = Column(Float, nullable=True)
    exit_at = Column(DateTime, nullable=True)
    pnl_pct = Column(Float, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "score": self.score,
            "entry_price": self.entry_price,
            "target": self.target,
            "stop_loss": self.stop_loss,
            "rr_ratio": self.rr_ratio,
            "atr": self.atr,
            "scanned_at": self.scanned_at.isoformat() if self.scanned_at else None,
            "scan_type": self.scan_type,
            "status": self.status,
            "exit_price": self.exit_price,
            "exit_at": self.exit_at.isoformat() if self.exit_at else None,
            "pnl_pct": self.pnl_pct,
        }


class TradeJournal(Base):
    __tablename__ = "trade_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False)
    direction = Column(String(20), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    qty = Column(Integer, nullable=False)
    entry_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    reason = Column(Text, nullable=True)
    emotion = Column(String(50), default="Calm")
    status = Column(String(20), default="OPEN")
    pnl = Column(Float, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "qty": self.qty,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "reason": self.reason,
            "emotion": self.emotion,
            "status": self.status,
            "pnl": self.pnl,
        }


class PredictionsHistory(Base):
    __tablename__ = "predictions_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    prediction_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    prediction_type = Column(String(20), nullable=False)
    entry_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    confidence_score = Column(Integer, nullable=False)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    adx = Column(Float, nullable=True)
    sector = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    vwap_distance = Column(Float, nullable=True)
    atr = Column(Float, nullable=True)
    news_score = Column(Float, nullable=True)
    market_breadth = Column(Float, nullable=True)
    sector_strength = Column(Float, nullable=True)
    nifty_trend = Column(String(20), nullable=True)
    actual_outcome = Column(Float, nullable=True)
    status = Column(String(20), default="PENDING")
    reason = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    manual_override_reason = Column(Text, nullable=True)
    setup_type = Column(String(50), nullable=True)
    market_regime_snapshot = Column(Text, nullable=True)
    risk_amount = Column(Float, nullable=True)
    confidence_probability = Column(Float, default=0.5)
    r_multiple = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    holding_time_minutes = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    pnl_inr = Column(Float, nullable=True)
    resolution_reason = Column(Text, nullable=True)
    regime_score = Column(Float, nullable=True)
    sector_score = Column(Float, nullable=True)
    volume_score = Column(Float, nullable=True)
    rs_score = Column(Float, nullable=True)
    trade_quality_score = Column(Float, nullable=True)
    correlation_score = Column(Float, nullable=True)
    signal_time = Column(DateTime, nullable=True)
    order_time = Column(DateTime, nullable=True)
    fill_time = Column(DateTime, nullable=True)
    fill_price = Column(Float, nullable=True)
    slippage_pct = Column(Float, nullable=True)
    broker_failure_reason = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EquityCurve(Base):
    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, nullable=False)
    equity_before = Column(Float, nullable=False)
    equity_after = Column(Float, nullable=False)
    peak_equity = Column(Float, nullable=False)
    drawdown_pct = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)


class MetricsCache(Base):
    __tablename__ = "metrics_cache"

    key = Column(String(100), primary_key=True)
    value_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PortfolioState(Base):
    __tablename__ = "portfolio_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    current_equity = Column(Float, nullable=False, default=100000.0)
    peak_equity = Column(Float, nullable=False, default=100000.0)
    daily_equity = Column(Float, nullable=False, default=100000.0)
    sector_exposure = Column(Text, default="{}")
    active_positions = Column(Text, default="[]")
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)


class StrategyHealth(Base):
    __tablename__ = "strategy_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setup_type = Column(String(100), nullable=False, unique=True)
    lifetime_pf = Column(Float, nullable=False)
    last_30_pf = Column(Float, nullable=False)
    last_90_pf = Column(Float, nullable=False)
    edge_score = Column(Float, default=0.0)
    status = Column(String(20), default="ACTIVE")


class ConfidenceCalibration(Base):
    __tablename__ = "confidence_calibration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    band = Column(String(50), nullable=False)
    regime = Column(String(50), nullable=False)
    predicted_win_rate = Column(Float, nullable=False)
    actual_win_rate = Column(Float, nullable=False)
    calibration_error = Column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("band", "regime", name="uix_band_regime"),)


import sqlalchemy

class DailyGovernanceReport(Base):
    __tablename__ = "daily_governance_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(String(20), nullable=False, unique=True)
    pf = Column(Float, nullable=False)
    ev = Column(Float, nullable=False)
    drawdown = Column(Float, nullable=False)
    regime = Column(String(50), nullable=False)
    best_strategy = Column(String(100), nullable=True)
    worst_strategy = Column(String(100), nullable=True)
    calibration_error = Column(Float, nullable=True)
    kill_switch_events = Column(Integer, default=0)
    exposure_violations = Column(Integer, default=0)
    data_confidence_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataQuality(Base):
    __tablename__ = "data_quality"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checked_at = Column(DateTime, default=datetime.utcnow)
    total_trades = Column(Integer, nullable=True)
    valid_trades = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    failures = Column(Text, nullable=True)
    locked = Column(Boolean, default=False)


class RiskSettings(Base):
    __tablename__ = "risk_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_loss_limit = Column(Float, nullable=False, default=-3.0)
    daily_drawdown_limit = Column(Float, nullable=False, default=-4.0)
    max_consecutive_losses = Column(Integer, nullable=False, default=5)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RejectedSignal(Base):
    __tablename__ = "rejected_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False)
    rejection_category = Column(String(100), nullable=False)
    rejection_reason = Column(Text, nullable=False)
    signal_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    status = Column(String(20), default="PENDING")
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AngelOneSession(Base):
    __tablename__ = "angelone_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_code = Column(String(50), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    pin_encrypted = Column(Text, nullable=False)
    totp_secret_encrypted = Column(Text, nullable=False)
    session_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    feed_token = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(200), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, index=True)
    description = Column(String(256))
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
        }
