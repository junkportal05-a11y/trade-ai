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

def test_expire_old_intraday(temp_db):
    """Test expiring intraday signals from previous days."""

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # We need to insert a few signals with specific dates
            with db._conn() as c:
                # 1. Intraday, PENDING, yesterday - SHOULD EXPIRE
                c.execute(
                    """INSERT INTO signals_history
                       (symbol, scan_type, status, scanned_at, signal_type, entry_price, name, sector, confidence, score, target, stop_loss)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("EXPIRE_ME", "INTRADAY", "PENDING", "2023-01-01 10:00:00", "BUY", 100.0, "EXPIRE_ME", "IT", 80, 8, 110.0, 90.0)
                )

                # 2. Intraday, PENDING, today - SHOULD STAY PENDING
                c.execute(
                    """INSERT INTO signals_history
                       (symbol, scan_type, status, scanned_at, signal_type, entry_price, name, sector, confidence, score, target, stop_loss)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("KEEP_ME", "INTRADAY", "PENDING", "2023-01-02 10:00:00", "BUY", 100.0, "KEEP_ME", "IT", 80, 8, 110.0, 90.0)
                )

                # 3. SWING, PENDING, yesterday - SHOULD STAY PENDING
                c.execute(
                    """INSERT INTO signals_history
                       (symbol, scan_type, status, scanned_at, signal_type, entry_price, name, sector, confidence, score, target, stop_loss)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("SWING_ME", "SWING", "PENDING", "2023-01-01 10:00:00", "BUY", 100.0, "SWING_ME", "IT", 80, 8, 110.0, 90.0)
                )

                # 4. Intraday, PROFIT, yesterday - SHOULD STAY PROFIT
                c.execute(
                    """INSERT INTO signals_history
                       (symbol, scan_type, status, scanned_at, signal_type, entry_price, name, sector, confidence, score, target, stop_loss)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("PROFIT_ME", "INTRADAY", "PROFIT", "2023-01-01 10:00:00", "BUY", 100.0, "PROFIT_ME", "IT", 80, 8, 110.0, 90.0)
                )
                c.commit()

            # Act: expire old intraday signals pretending today is 2023-01-02
            with patch("backend.db._now_ist", return_value="2023-01-02 15:30:00"):
                db.expire_old_intraday()

            # Assert
            with db._conn() as c:
                rows = c.execute("SELECT symbol, status, exit_at FROM signals_history").fetchall()

                # Check status
                status_map = {r["symbol"]: r["status"] for r in rows}
                exit_at_map = {r["symbol"]: r["exit_at"] for r in rows}

                assert status_map["EXPIRE_ME"] == "EXPIRED"
                assert exit_at_map["EXPIRE_ME"] == "2023-01-02 15:30:00"

                assert status_map["KEEP_ME"] == "PENDING"
                assert exit_at_map["KEEP_ME"] is None

                assert status_map["SWING_ME"] == "PENDING"

                assert status_map["PROFIT_ME"] == "PROFIT"
