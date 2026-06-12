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

def test_get_stats(temp_db):
    """Test get_stats returns correct aggregated statistics."""

    mock_signals = [
        # Signal 1: PENDING
        {
            "symbol": "TCS", "name": "TCS Ltd", "sector": "IT",
            "direction": "BUY", "signal_type": "BUY", "confidence": 80,
            "score": 8, "entry": 100.0, "entry_price": 100.0,
            "target": 110.0, "stop_loss": 90.0, "rr_ratio": 1.0,
            "atr": 2.0, "scan_type": "intraday"
        },
        # Signal 2: HIT_TARGET (Won)
        {
            "symbol": "INFY", "name": "Infosys", "sector": "IT",
            "direction": "BUY", "signal_type": "BUY", "confidence": 85,
            "score": 9, "entry": 200.0, "entry_price": 200.0,
            "target": 220.0, "stop_loss": 190.0, "rr_ratio": 2.0,
            "atr": 4.0, "scan_type": "intraday"
        },
        # Signal 3: HIT_STOP (Lost)
        {
            "symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "FINANCE",
            "direction": "SELL", "signal_type": "SELL", "confidence": 75,
            "score": 7, "entry": 1500.0, "entry_price": 1500.0,
            "target": 1400.0, "stop_loss": 1550.0, "rr_ratio": 2.0,
            "atr": 20.0, "scan_type": "intraday"
        }
    ]

    with patch("backend.db.DB_PATH", str(temp_db)):
        with patch("backend.db.IS_POSTGRES", False):
            # Act: Add the signals
            sig1_id = db.add_signal(mock_signals[0])
            sig2_id = db.add_signal(mock_signals[1])
            sig3_id = db.add_signal(mock_signals[2])

            # Update to HIT_TARGET and HIT_STOP
            # INFY: Won 10%
            db.update_signal(sig2_id, "HIT_TARGET", 220.0, 10.0)
            # HDFCBANK: Lost 3.33%
            db.update_signal(sig3_id, "HIT_STOP", 1550.0, -3.33)

            stats = db.get_stats()

            # Assertions
            assert stats["total"] == 3
            assert stats["pending"] == 1
            assert stats["won"] == 1
            assert stats["lost"] == 1
            assert stats["resolved"] == 2
            assert stats["win_rate"] == 50.0
            assert stats["avg_pnl"] == 3.33  # (10.0 - 3.33) / 2 = 3.335 ~ 3.34

            # Verify Phase Omega keys are present
            assert "portfolio" in stats
            assert "governance" in stats
            assert "kill_switch" in stats
