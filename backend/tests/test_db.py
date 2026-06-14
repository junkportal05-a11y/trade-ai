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


def test_init_db(tmp_path):
    """Test that the init_db function creates the required database tables correctly."""
    test_db_path = tmp_path / "test_init_db.db"

    with patch("backend.db.DB_PATH", str(test_db_path)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Initialize the database
            db.init_db()

            # Assert: Verify that the expected tables were created
            with db._conn() as c:
                # Check signals_history
                c.execute("PRAGMA table_info(signals_history)")
                sig_columns = [row[1] for row in c.fetchall()]
                assert len(sig_columns) > 0
                assert "id" in sig_columns
                assert "symbol" in sig_columns
                assert "rr_ratio" in sig_columns # Checks migration worked

                # Check predictions_history
                c.execute("PRAGMA table_info(predictions_history)")
                pred_columns = [row[1] for row in c.fetchall()]
                assert len(pred_columns) > 0
                assert "id" in pred_columns
                assert "symbol" in pred_columns
                assert "sector" in pred_columns # Checks migration worked

                # Check trade_journal
                c.execute("PRAGMA table_info(trade_journal)")
                trade_columns = [row[1] for row in c.fetchall()]
                assert len(trade_columns) > 0
                assert "id" in trade_columns
                assert "symbol" in trade_columns

                # Check metrics_cache
                c.execute("PRAGMA table_info(metrics_cache)")
                metrics_columns = [row[1] for row in c.fetchall()]
                assert len(metrics_columns) > 0
                assert "key" in metrics_columns


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
