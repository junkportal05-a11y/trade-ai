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

def test_get_pending_signals(temp_db):
    """Test retrieving pending signals."""

    mock_signal_1 = {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank",
        "sector": "Banking",
        "direction": "BUY",
        "signal_type": "BUY",
        "confidence": 85,
        "score": 8,
        "entry": 1600.0,
        "entry_price": 1600.0,
        "target": 1650.0,
        "stop_loss": 1550.0,
        "rr_ratio": 1.0,
        "atr": 10.0,
        "scan_type": "intraday",
    }

    mock_signal_2 = {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank",
        "sector": "Banking",
        "direction": "SELL",
        "signal_type": "SELL",
        "confidence": 75,
        "score": 7,
        "entry": 1000.0,
        "entry_price": 1000.0,
        "target": 950.0,
        "stop_loss": 1050.0,
        "rr_ratio": 1.0,
        "atr": 8.0,
        "scan_type": "intraday",
    }

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Add two signals
            signal_id_1 = db.add_signal(mock_signal_1)
            signal_id_2 = db.add_signal(mock_signal_2)

            assert signal_id_1 is not None
            assert signal_id_2 is not None

            # Update the first signal to not be PENDING
            db.update_signal(signal_id_1, "PROFIT", 1650.0, 3.12)

            # Act: Get pending signals
            pending_signals = db.get_pending_signals()

            # Assert: Verify only the second signal is returned
            assert len(pending_signals) == 1
            assert pending_signals[0]["id"] == signal_id_2
            assert pending_signals[0]["symbol"] == "ICICIBANK"
            assert pending_signals[0]["status"] == "PENDING"
