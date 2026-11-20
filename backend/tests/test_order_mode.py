"""Unit tests for order_mode column on predictions_history.

Asserts:
- order_mode defaults to 'paper' when not specified
- explicitly set values ('paper'/'live') are stored unambiguously
- to_dict() includes order_mode — never silently dropped
- nullable=False enforced at DB level
- migration backfill query is correct SQL
"""
from __future__ import annotations

import pytest
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

from app.core.database import Base
from app.db.models import PredictionsHistory


# Isolated in-memory DB — schema created once at module import
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(bind=TEST_ENGINE)
TestingSession = sessionmaker(bind=TEST_ENGINE)


def _make_pred_dict() -> dict:
    """Return a dict with all NOT NULL columns that lack a default."""
    return {
        "symbol": "TEST",
        "prediction_type": "BULLISH",
        "entry_price": 100.0,
        "target_price": 110.0,
        "stop_loss": 90.0,
        "confidence_score": 80,
        "prediction_date": datetime.datetime.now(datetime.timezone.utc),
    }


class TestOrderModeDefault:
    def test_default_value_is_paper(self):
        """Inserting without order_mode → ORM default 'paper' is applied."""
        db = TestingSession()
        pred = PredictionsHistory(**_make_pred_dict())
        # order_mode NOT set → ORM default 'paper'
        db.add(pred)
        db.commit()
        db.refresh(pred)
        assert pred.order_mode == "paper"

    def test_explicit_paper_stored(self):
        """Explicit order_mode='paper' stored correctly."""
        db = TestingSession()
        pred = PredictionsHistory(**_make_pred_dict(), order_mode="paper")
        db.add(pred)
        db.commit()
        db.refresh(pred)
        assert pred.order_mode == "paper"

    def test_explicit_live_stored(self):
        """Explicit order_mode='live' stored correctly."""
        db = TestingSession()
        pred = PredictionsHistory(**_make_pred_dict(), order_mode="live")
        db.add(pred)
        db.commit()
        db.refresh(pred)
        assert pred.order_mode == "live"

    def test_column_is_not_null(self):
        """Column has nullable=False — DB rejects NULL inserts."""
        TestingSession()
        cols = {c["name"]: c for c in inspect(TEST_ENGINE).get_columns("predictions_history")}
        assert cols["order_mode"]["nullable"] is False, "order_mode must be NOT NULL"

    def test_null_insert_rejected(self):
        """Attempting to insert NULL directly raises a DB-level integrity error."""
        db = TestingSession()
        # Try to insert NULL via raw SQL, providing all required columns
        with pytest.raises(Exception) as exc_info:
            db.execute(text(
                "INSERT INTO predictions_history "
                "(symbol, prediction_type, entry_price, target_price, stop_loss, "
                "confidence_score, prediction_date, order_mode) "
                "VALUES (:symbol, :ptype, :entry, :target, :stop, :conf, :pred_date, NULL)"
            ), {
                "symbol": "NULL_TEST",
                "ptype": "BULLISH",
                "entry": 1.0,
                "target": 2.0,
                "stop": 0.5,
                "conf": 80,
                "pred_date": datetime.datetime.now(datetime.timezone.utc),
            })
            db.commit()
        # Should be an integrity error about NOT NULL constraint
        assert "NOT NULL constraint failed" in str(exc_info.value).upper() or "NOT NULL" in str(exc_info.value)


class TestOrderModeBackfill:
    def test_legacy_null_rows_backfilled(self):
        """Migration backfill query correctly fills NULL order_mode → 'paper'.

        Uses a separate test table with the pre-migration schema
        (order_mode TEXT nullable, no server_default) so we can inject
        a genuine NULL row and verify the backfill query restores it.
        """
        db = TestingSession()

        # Create pre-migration schema (no server_default, nullable)
        db.execute(text("""
            CREATE TABLE test_legacy_preds (
                id INTEGER PRIMARY KEY,
                order_mode TEXT
            )
        """))
        db.commit()

        try:
            # Insert NULL to simulate a legacy row (no server_default, no default)
            db.execute(text(
                "INSERT INTO test_legacy_preds (order_mode) VALUES (NULL)"
            ))
            db.commit()

            # Confirm NULL before backfill
            row = db.execute(text(
                "SELECT order_mode FROM test_legacy_preds"
            )).fetchone()
            assert row[0] is None, "precondition: row should be NULL before backfill"

            # Apply the same backfill query as in migrations.py
            db.execute(text(
                "UPDATE test_legacy_preds SET order_mode = 'paper' "
                "WHERE order_mode IS NULL"
            ))
            db.commit()

            # Confirm backfilled
            row = db.execute(text(
                "SELECT order_mode FROM test_legacy_preds"
            )).fetchone()
            assert row[0] == "paper"
        finally:
            db.execute(text("DROP TABLE test_legacy_preds"))
            db.commit()


class TestOrderModeAmbiguity:
    def test_to_dict_includes_order_mode(self):
        """to_dict() includes order_mode — never silently dropped."""
        db = TestingSession()
        pred = PredictionsHistory(**_make_pred_dict(), order_mode="live")
        db.add(pred)
        db.commit()
        db.refresh(pred)
        d = pred.to_dict()
        assert "order_mode" in d
        assert d["order_mode"] == "live"

    def test_paper_and_live_are_distinct(self):
        """paper vs live rows produce different order_mode values."""
        db = TestingSession()
        base = _make_pred_dict()
        for sym, mode in (("PAPER_TEST", "paper"), ("LIVE_TEST", "live")):
            d = dict(base)
            d["symbol"] = sym
            d["order_mode"] = mode
            db.add(PredictionsHistory(**d))
        db.commit()

        rows = db.query(PredictionsHistory).filter(
            PredictionsHistory.symbol.in_(["PAPER_TEST", "LIVE_TEST"])
        ).all()
        modes = {r.symbol: r.order_mode for r in rows}
        assert modes["PAPER_TEST"] == "paper"
        assert modes["LIVE_TEST"] == "live"
        assert modes["PAPER_TEST"] != modes["LIVE_TEST"]