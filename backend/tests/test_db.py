import pytest
from unittest.mock import patch

import backend.db as db


@pytest.fixture
def temp_db(tmp_path):
    """Fixture to create a temporary database for testing."""
    test_db_path = tmp_path / "test_trading.db"

    with patch("backend.db.DB_PATH", str(test_db_path)):
        with patch("backend.db.IS_POSTGRES", False):
            db.init_db()
            yield test_db_path


def test_update_signal(temp_db):
    """Test updating an existing signal's status, exit price, and pnl_pct."""

    mock_signal = {
        "symbol": "TCS",
        "name": "TCS Ltd",
        "sector": "IT",
        "direction": "BUY",
        "signal_type": "BUY",
        "confidence": 80,
        "score": 8,
        "entry": 100.0,
        "entry_price": 100.0,
        "target": 110.0,
        "stop_loss": 90.0,
        "rr_ratio": 1.0,
        "atr": 2.0,
        "scan_type": "intraday",
    }

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Add the signal
            signal_id = db.add_signal(mock_signal)
            assert signal_id is not None

            # Act: Update the signal
            db.update_signal(signal_id, "PROFIT", 110.0, 10.0)

            # Assert: Verify the update
            with db._conn() as c:
                row = c.execute(
                    "SELECT * FROM signals_history WHERE id=?", (signal_id,)
                ).fetchone()
                assert row is not None

                # Check updated fields
                assert row["status"] == "PROFIT"
                assert row["exit_price"] == 110.0
                assert row["pnl_pct"] == 10.0
                assert row["exit_at"] is not None


def test_clear_history(temp_db):
    """Test clearing all records from the signals_history table."""

    mock_signal = {
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "sector": "Energy",
        "direction": "BUY",
        "signal_type": "BUY",
        "confidence": 90,
        "score": 9,
        "entry": 2500.0,
        "entry_price": 2500.0,
        "target": 2600.0,
        "stop_loss": 2400.0,
        "rr_ratio": 1.0,
        "atr": 50.0,
        "scan_type": "intraday",
    }

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Add a signal
            signal_id = db.add_signal(mock_signal)
            assert signal_id is not None

            # Assert: Verify the signal was added
            with db._conn() as c:
                row = c.execute(
                    "SELECT COUNT(*) FROM signals_history"
                ).fetchone()
                assert row[0] == 1

            # Act: Clear history
            db.clear_history()

            # Assert: Verify the table is empty
            with db._conn() as c:
                row = c.execute(
                    "SELECT COUNT(*) FROM signals_history"
                ).fetchone()
                assert row[0] == 0


def test_add_journal_entry(temp_db):
    """Test adding a trade journal entry."""

    mock_entry = {
        "symbol": "INFY",
        "direction": "SELL",
        "entry_price": "1500.50",
        "exit_price": "1450.00",
        "qty": "50",
        "entry_date": "2024-06-14T10:00:00Z",
        "reason": "Technical Breakout",
        "emotion": "Confident",
        "status": "CLOSED",
        "pnl": "2525.0",
    }

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Add journal entry
            entry_id = db.add_journal_entry(mock_entry)
            assert entry_id is not None

            # Assert: Verify the entry was added
            with db._conn() as c:
                row = c.execute(
                    "SELECT * FROM trade_journal WHERE id=?", (entry_id,)
                ).fetchone()

                assert row is not None
                assert row["symbol"] == "INFY"
                assert row["direction"] == "SELL"
                assert row["entry_price"] == 1500.50
                assert row["exit_price"] == 1450.00
                assert row["qty"] == 50
                assert row["entry_date"] == "2024-06-14T10:00:00Z"
                assert row["reason"] == "Technical Breakout"
                assert row["emotion"] == "Confident"
                assert row["status"] == "CLOSED"
                assert row["pnl"] == 2525.0
