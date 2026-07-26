"""Delete the seeded dummy signal by its id."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import db

with db._conn() as c:
    cur = c.execute("SELECT id FROM signals_history WHERE symbol='TCS' AND status='CLOSED'")
    row = cur.fetchone()
    if row and row[0]:
        c.execute("DELETE FROM signals_history WHERE id = ?", (row[0],))
        c.commit()
    else:
        print("TCS signal row not found")
    cur.close()
    print("Deleted TCS signal row if existed")