"""Verify real resolved trades exist in the connected Supabase PostgreSQL DB."""
import os
import sys

# Load DATABASE_URL directly from backend/.env (no dotenv dependency needed)
env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
db_url = None
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            db_url = line[len("DATABASE_URL="):].strip()
            break

if not db_url:
    print("ERROR: DATABASE_URL not found in backend/.env")
    sys.exit(1)

# Mask for logging (never print the real credential)
masked = db_url
try:
    # postgresql://user:pass@host:port/db -> show user/host only
    scheme, rest = db_url.split("://", 1)
    userhost, dbpart = rest.split("@", 1)
    user = userhost.split(":")[0]
    host = dbpart.split("/")[0]
    masked = f"{scheme}://{user}:****@{host}/..."
except Exception:
    masked = "<unparseable>"
print(f"Connecting to Supabase: {masked}")

import psycopg2

try:
    conn = psycopg2.connect(db_url)
except Exception as e:
    print(f"ERROR: connection failed: {e}")
    sys.exit(1)

cur = conn.cursor()

ALLOWED_TABLES = {"predictions_history", "signals_history", "trade_journal"}

def count_where(table, where):
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table}")
    if where == "1=1":
        cur.execute(f"SELECT COUNT(*) FROM {table}")
    elif "NOT IN" in where:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE status NOT IN ('PENDING','ACTIVE')")
    elif "IS NOT NULL" in where:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE pnl IS NOT NULL")
    else:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE 1=1")
    return cur.fetchone()[0]

print("\n=== Resolved trades in Supabase ===")

pred_total = count_where("predictions_history", "1=1")
pred_resolved = count_where("predictions_history", "status NOT IN ('PENDING','ACTIVE')")
print(f"predictions_history: total={pred_total}, resolved={pred_resolved}")
if pred_resolved:
    cur.execute(
        "SELECT id, symbol, prediction_type, entry_price, target_price, stop_loss, "
        "actual_outcome, pnl_pct, status, resolved_at "
        "FROM predictions_history WHERE status NOT IN ('PENDING','ACTIVE') "
        "ORDER BY resolved_at DESC NULLS LAST LIMIT 5"
    )
    for r in cur.fetchall():
        print("  pred:", r)

sig_total = count_where("signals_history", "1=1")
sig_resolved = count_where("signals_history", "status NOT IN ('PENDING','ACTIVE')")
print(f"signals_history: total={sig_total}, resolved={sig_resolved}")
if sig_resolved:
    cur.execute(
        "SELECT id, symbol, signal_type, entry_price, target, stop_loss, "
        "exit_price, pnl_pct, status, exit_at "
        "FROM signals_history WHERE status NOT IN ('PENDING','ACTIVE') "
        "ORDER BY exit_at DESC NULLS LAST LIMIT 5"
    )
    for r in cur.fetchall():
        print("  signal:", r)

tj_total = count_where("trade_journal", "1=1")
tj_resolved = count_where("trade_journal", "pnl IS NOT NULL")
print(f"trade_journal: total={tj_total}, with_pnl={tj_resolved}")
if tj_resolved:
    cur.execute(
        "SELECT id, symbol, direction, entry_price, exit_price, qty, pnl, entry_date "
        "FROM trade_journal WHERE pnl IS NOT NULL ORDER BY entry_date DESC LIMIT 5"
    )
    for r in cur.fetchall():
        print("  journal:", r)

cur.close()
conn.close()

print("\n=== Summary ===")
any_resolved = pred_resolved or sig_resolved or tj_resolved
print("REAL RESOLVED TRADES FOUND:" , bool(any_resolved))
