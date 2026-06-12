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

def test_update_signals_batch(temp_db):
    """Test updating multiple existing signals in batch."""

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Add multiple signals
            id1 = db.add_signal({"symbol": "S1", "name": "N1", "sector": "Sec", "direction": "BUY", "signal_type": "BUY", "confidence": 80, "score": 8, "entry": 100.0, "entry_price": 100.0, "target": 110.0, "stop_loss": 90.0, "rr_ratio": 1.0, "atr": 2.0, "scan_type": "intraday"})
            id2 = db.add_signal({"symbol": "S2", "name": "N2", "sector": "Sec", "direction": "SELL", "signal_type": "SELL", "confidence": 80, "score": 8, "entry": 100.0, "entry_price": 100.0, "target": 90.0, "stop_loss": 110.0, "rr_ratio": 1.0, "atr": 2.0, "scan_type": "intraday"})

            # Act: Update the signals in batch
            updates = [
                ("HIT_TARGET", 110.0, "2024-01-01 10:00:00", 10.0, id1),
                ("HIT_STOP", 110.0, "2024-01-01 10:00:00", -10.0, id2)
            ]
            db.update_signals_batch(updates)

            # Assert: Verify the updates
            with db._conn() as c:
                row1 = c.execute("SELECT * FROM signals_history WHERE id=?", (id1,)).fetchone()
                row2 = c.execute("SELECT * FROM signals_history WHERE id=?", (id2,)).fetchone()

                assert row1["status"] == "HIT_TARGET"
                assert row1["exit_price"] == 110.0
                assert row1["pnl_pct"] == 10.0

                assert row2["status"] == "HIT_STOP"
                assert row2["exit_price"] == 110.0
                assert row2["pnl_pct"] == -10.0
