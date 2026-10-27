"""Database migrations and schema initialization."""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.models import (
    SignalHistory,
    TradeJournal,
    PredictionsHistory,
    EquityCurve,
    MetricsCache,
    PortfolioState,
    StrategyHealth,
    ConfidenceCalibration,
    DailyGovernanceReport,
    DataQuality,
    RiskSettings,
    RejectedSignal,
    AngelOneSession,
    AppSettings,
)

logger = logging.getLogger(__name__)

_ALL_MODELS = [
    SignalHistory,
    TradeJournal,
    PredictionsHistory,
    EquityCurve,
    MetricsCache,
    PortfolioState,
    StrategyHealth,
    ConfidenceCalibration,
    DailyGovernanceReport,
    DataQuality,
    RiskSettings,
    RejectedSignal,
    AngelOneSession,
    AppSettings,
]


def _get_existing_columns(conn, table_name: str) -> set[str]:
    """Safely get existing column names without SQL injection."""
    try:
        inspector = inspect(conn)
        cols = inspector.get_columns(table_name)
        return {c["name"] for c in cols}
    except Exception:
        return set()


def _add_column_safe(engine: Engine, table_name: str, col_name: str, col_type: str) -> None:
    """Add a column if it doesn't exist. Uses text() for safe DDL."""
    with engine.begin() as conn:
        existing = _get_existing_columns(conn, table_name)
        if col_name not in existing:
            # Only allow specific safe column names and types
            safe_types = {"TEXT", "REAL", "INTEGER", "BOOLEAN", "DateTime", "DATETIME"}
            if col_type.upper() not in safe_types:
                logger.warning(f"Skipping unsafe column type: {col_type}")
                return
            # Use text() with bound params for the value, but DDL syntax needs raw
            stmt = text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}')
            conn.execute(stmt)
            logger.info(f"Added column {col_name} to {table_name}")


def run_migrations(engine: Engine) -> None:
    """Create all tables and run any pending migrations."""
    from app.core.database import Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    # ── Migration: add missing columns ──────────────────────────────────
    _add_column_safe(engine, "trade_journal", "user_id", "TEXT")

    # ── Migration: assign pre-existing journal rows with NULL user_id to 'legacy' sentinel ──
    # Application-layer access treats user_id as required; pre-existing rows that lack one
    # are orphaned and would otherwise be invisible to every user. Assigning them to the
    # sentinel 'legacy' preserves the data and makes it discoverable (query with user_id='legacy').
    with engine.begin() as conn:
        conn.execute(text("UPDATE trade_journal SET user_id = 'legacy' WHERE user_id IS NULL"))
        logger.info("Assigned legacy trade_journal rows (NULL user_id) to 'legacy' sentinel user")

    _add_column_safe(engine, "predictions_history", "user_id", "TEXT")
    with engine.begin() as conn:
        conn.execute(text("UPDATE predictions_history SET user_id = 'legacy' WHERE user_id IS NULL"))
        logger.info("Assigned legacy predictions_history rows (NULL user_id) to 'legacy' sentinel user")

    _add_column_safe(engine, "signals_history", "rr_ratio", "REAL")
    _add_column_safe(engine, "signals_history", "atr", "REAL")

    pred_columns = [
        ("sector", "TEXT"),
        ("market_cap", "REAL"),
        ("volume_ratio", "REAL"),
        ("vwap_distance", "REAL"),
        ("atr", "REAL"),
        ("news_score", "REAL"),
        ("market_breadth", "REAL"),
        ("sector_strength", "REAL"),
        ("nifty_trend", "TEXT"),
        ("manual_override_reason", "TEXT"),
        ("position_size", "REAL"),
        ("setup_type", "TEXT"),
        ("market_regime_snapshot", "TEXT"),
        ("risk_amount", "REAL"),
        ("confidence_probability", "REAL"),
        ("r_multiple", "REAL"),
        ("exit_price", "REAL"),
        ("holding_time_minutes", "REAL"),
        ("pnl_pct", "REAL"),
        ("pnl_inr", "REAL"),
        ("resolution_reason", "TEXT"),
        ("regime_score", "REAL"),
        ("sector_score", "REAL"),
        ("volume_score", "REAL"),
        ("rs_score", "REAL"),
        ("trade_quality_score", "REAL"),
        ("correlation_score", "REAL"),
        ("signal_time", "DateTime"),
        ("order_time", "DateTime"),
        ("fill_time", "DateTime"),
        ("fill_price", "REAL"),
        ("slippage_pct", "REAL"),
        ("broker_failure_reason", "TEXT"),
        ("order_mode", "TEXT"),
    ]
    for col_name, col_type in pred_columns:
        _add_column_safe(engine, "predictions_history", col_name, col_type)

    _add_column_safe(engine, "strategy_health", "edge_score", "REAL")
    _add_column_safe(engine, "daily_governance_reports", "data_confidence_score", "REAL")
    _add_column_safe(engine, "daily_governance_reports", "created_at", "DateTime")

    # Safe alter column type for actual_outcome in PostgreSQL
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE predictions_history ALTER COLUMN actual_outcome TYPE VARCHAR(50) USING actual_outcome::text;"))
    except Exception:
        pass

    # ── Seed data ───────────────────────────────────────────────────────
    from sqlalchemy.orm import Session

    with Session(bind=engine) as session:
        # Risk settings
        risk_count = session.query(RiskSettings).count()
        if risk_count == 0:
            session.add(RiskSettings(
                daily_loss_limit=-3.0,
                daily_drawdown_limit=-4.0,
                max_consecutive_losses=5,
            ))
            session.commit()

        # Portfolio state
        port_count = session.query(PortfolioState).count()
        if port_count == 0:
            session.add(PortfolioState(
                current_equity=100_000.0,
                peak_equity=100_000.0,
                daily_equity=100_000.0,
                sector_exposure="{}",
                active_positions="[]",
            ))
            session.commit()

    logger.info("Migrations and seed data complete.")
