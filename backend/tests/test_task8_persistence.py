"""TAR-20 Task 8 add-on: data_source + journal target/stop persistence across DB layers.

Layers under test:
1. migrations.py _add_column_safe adds the new nullable columns to PRE-GATE legacy
   schemas (fresh-old sqlite file), so existing deployments don't lose provenance.
2. legacy sqlite insert paths (db.add_prediction / db.add_journal_entry) persist
   and round-trip the new columns.
3. SQLAlchemy insert paths (repositories via the /api/journal route) persist
   target_price/stop_loss/data_source keys the frontend already sends (83b872c).
"""
import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import db as legacy_db
from app.main import app
from app.core.security import require_session
from app.core.database import Base, get_db
from app.db.migrations import run_migrations
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ── helpers ───────────────────────────────────────────────────────────────────
def _create_pre_gate_schema(engine_path: str) -> None:
    """Build trade_journal / predictions_history WITHOUT the new columns.

    Mirrors the pre-TAR-20 schema so run_migrations() has real work to do.
    """
    conn = sqlite3.connect(engine_path)
    conn.executescript(
        """
        CREATE TABLE trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            qty INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            reason TEXT,
            emotion TEXT,
            status TEXT,
            pnl REAL
        );
        CREATE TABLE predictions_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            symbol TEXT NOT NULL,
            prediction_date TIMESTAMP NOT NULL,
            prediction_type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            target_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            confidence_score INTEGER NOT NULL,
            rsi REAL, macd REAL, adx REAL,
            sector TEXT, market_cap REAL, volume_ratio REAL, vwap_distance REAL,
            atr REAL, news_score REAL, market_breadth REAL, sector_strength REAL,
            nifty_trend TEXT, status TEXT, reason TEXT, resolved_at TIMESTAMP,
            manual_override_reason TEXT, setup_type TEXT, market_regime_snapshot TEXT,
            risk_amount REAL, confidence_probability REAL, r_multiple REAL,
            exit_price REAL, holding_time_minutes REAL, pnl_pct REAL, pnl_inr REAL,
            resolution_reason TEXT, regime_score REAL, sector_score REAL,
            volume_score REAL, rs_score REAL, trade_quality_score REAL,
            correlation_score REAL, signal_time TIMESTAMP, order_time TIMESTAMP,
            fill_time TIMESTAMP, fill_price REAL, slippage_pct REAL,
            broker_failure_reason TEXT, order_mode TEXT, position_size REAL
        );
        """
    )
    conn.commit()
    conn.close()


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


# ── 1. migration smoke on a legacy deployment ────────────────────────────────
def test_migration_adds_persistence_columns_to_legacy_schema(tmp_path):
    db_file = str(tmp_path / "legacy.db")
    _create_pre_gate_schema(db_file)
    engine = create_engine(f"sqlite:///{db_file}")

    run_migrations(engine)

    conn = sqlite3.connect(db_file)
    try:
        journal_cols = _columns(conn, "trade_journal")
        pred_cols = _columns(conn, "predictions_history")
    finally:
        conn.close()

    assert "data_source" in journal_cols
    assert "target_price" in journal_cols
    assert "stop_loss" in journal_cols
    assert "data_source" in pred_cols
    # re-run must be idempotent (_add_column_safe)
    run_migrations(engine)


# ── 2. legacy sqlite insert paths ────────────────────────────────────────────
def test_legacy_journal_persists_target_stop_data_source(monkeypatch, tmp_path):
    db_file = str(tmp_path / "legacy_j.db")
    _create_pre_gate_schema(db_file)
    engine = create_engine(f"sqlite:///{db_file}")
    run_migrations(engine)

    monkeypatch.setattr(legacy_db, "engine", engine)
    monkeypatch.setattr(legacy_db, "IS_POSTGRES", False)

    entry_id = legacy_db.add_journal_entry(
        {
            "symbol": "tcs.ns",
            "direction": "BUY",
            "entry_price": 3500.0,
            "qty": 10,
            "data_source": "angelone",
            "target_price": 3625.0,
            "stop_loss": 3440.0,
        }
    )
    rows = legacy_db.get_journal_entries()
    row = next(r for r in rows if r["id"] == entry_id)
    assert row["data_source"] == "angelone"
    assert row["target_price"] == 3625.0
    assert row["stop_loss"] == 3440.0

    # pre-gate callers that never send the keys keep working (nullable defaults)
    plain_id = legacy_db.add_journal_entry(
        {"symbol": "infy.ns", "direction": "SELL", "entry_price": 1500.0, "qty": 5}
    )
    fresh = legacy_db.get_journal_entries()
    plain_row = next(r for r in fresh if r["id"] == plain_id)
    assert plain_row["data_source"] is None
    assert plain_row["target_price"] is None
    assert plain_row["stop_loss"] is None


def test_legacy_prediction_persists_data_source(monkeypatch, tmp_path):
    db_file = str(tmp_path / "legacy_p.db")
    _create_pre_gate_schema(db_file)
    engine = create_engine(f"sqlite:///{db_file}")
    run_migrations(engine)

    monkeypatch.setattr(legacy_db, "engine", engine)
    monkeypatch.setattr(legacy_db, "IS_POSTGRES", False)

    pred_id = legacy_db.add_prediction(
        {
            "symbol": "reliance.ns",
            "prediction_type": "BULLISH",
            "entry_price": 2850.0,
            "target_price": 2950.0,
            "stop_loss": 2800.0,
            "confidence_score": 78,
            "rsi": 55.0,
            "macd": 1.2,
            "adx": 25.0,
            "sector": "Energy",
            "market_cap": 1900000.0,
            "volume_ratio": 1.4,
            "vwap_distance": 0.3,
            "data_source": "yfinance",
        }
    )
    rows = legacy_db.get_predictions()
    row = next(r for r in rows if r["id"] == pred_id)
    assert row["data_source"] == "yfinance"


# ── 3. SQLAlchemy layer via the journal API ──────────────────────────────────
def test_journal_api_persists_frontend_keys():
    engine = _test_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_session] = lambda: {
        "username": "kevin",
        "role": "Trader",
        "clearance": "LEVEL_2_TRADER",
    }
    try:
        client = TestClient(app)
        res = client.post(
            "/api/journal",
            json={
                "symbol": "TCS.NS",
                "direction": "BUY",
                "entry_price": 3500.0,
                "qty": 10,
                "target_price": 3625.0,
                "stop_loss": 3440.0,
                "data_source": "angelone",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["target_price"] == 3625.0
        assert body["stop_loss"] == 3440.0
        assert body["data_source"] == "angelone"

        listed = client.get("/api/journal").json()
        row = next(r for r in listed if r["id"] == body["id"])
        assert row["data_source"] == "angelone"
        assert row["target_price"] == 3625.0
        assert row["stop_loss"] == 3440.0
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_session, None)
        engine.dispose()
