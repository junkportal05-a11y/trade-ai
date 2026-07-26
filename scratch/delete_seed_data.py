"""Delete the seeded dummy trades created by seed_dummy_data.py."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import db

with db._conn() as c:
    c.execute("DELETE FROM predictions_history WHERE symbol='RELIANCE' AND status='WIN' AND pnl_pct=5.0")
    pred = c.rowcount
    c.execute("DELETE FROM signals_history WHERE symbol='TCS' AND status='CLOSED'")
    sig = c.rowcount
    c.execute("DELETE FROM trade_journal WHERE symbol='INFY' AND status='CLOSED' AND pnl=500.0")
    tj = c.rowcount
    c.commit()

print(f"Deleted dummy rows -> predictions:{pred} signals:{sig} journal:{tj}")
