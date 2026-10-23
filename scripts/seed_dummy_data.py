import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
import db

now = datetime.now(timezone.utc).isoformat()

with db._conn() as c:
    c.execute(
        "INSERT INTO predictions_history (symbol, prediction_date, prediction_type, entry_price, target_price, stop_loss, confidence_score, status, actual_outcome, resolved_at, pnl_pct, pnl_inr) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
        ('RELIANCE', now, 'BUY', 2000, 2100, 1950, 85, 'WIN', 2100, now, 5.0, 100)
    )
    c.execute(
        "INSERT INTO signals_history (symbol, name, sector, signal_type, confidence, score, entry_price, target, stop_loss, scanned_at, scan_type, status, exit_price, exit_at, pnl_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
        ('TCS', 'TCS', 'IT', 'SELL', 90, 8, 3000, 2900, 3050, now, 'INTRADAY', 'CLOSED', 2900, now, 3.33)
    )
    c.execute(
        "INSERT INTO trade_journal (symbol, direction, entry_price, exit_price, qty, entry_date, status, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
        ('INFY', 'BUY', 1500, 1550, 10, now, 'CLOSED', 500)
    )
    c.commit()

print("Seeded database with dummy resolved trades.")
