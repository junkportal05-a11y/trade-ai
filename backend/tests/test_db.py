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


def test_get_history(temp_db):
    """Test retrieving history with and without filters."""
    mock_signal_1 = {
        "symbol": "TCS", "name": "TCS Ltd", "sector": "IT", "direction": "BUY",
        "signal_type": "BUY", "confidence": 80, "score": 8, "entry": 100.0,
        "entry_price": 100.0, "target": 110.0, "stop_loss": 90.0, "rr_ratio": 1.0,
        "atr": 2.0, "scan_type": "intraday",
    }
    mock_signal_2 = {
        "symbol": "RELIANCE", "name": "Reliance", "sector": "Energy", "direction": "SELL",
        "signal_type": "SELL", "confidence": 90, "score": 9, "entry": 2500.0,
        "entry_price": 2500.0, "target": 2400.0, "stop_loss": 2600.0, "rr_ratio": 1.0,
        "atr": 50.0, "scan_type": "intraday",
    }

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            id1 = db.add_signal(mock_signal_1)
            id2 = db.add_signal(mock_signal_2)

            # Update signal 1 to PROFIT status
            db.update_signal(id1, "PROFIT", 110.0, 10.0)

            # Test getting all history
            history = db.get_history()
            assert len(history) == 2

            # Test symbol filter
            tcs_history = db.get_history(symbol="TCS")
            assert len(tcs_history) == 1
            assert tcs_history[0]["symbol"] == "TCS"

            # Test status filter
            profit_history = db.get_history(status="PROFIT")
            assert len(profit_history) == 1
            assert profit_history[0]["status"] == "PROFIT"

            # Test limit
            limited_history = db.get_history(limit=1)
            assert len(limited_history) == 1
