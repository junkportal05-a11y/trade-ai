"""
db.py — SQLite signal history & backtesting engine
====================================================
Zero external setup: uses a local SQLite file at backend/trading_platform.db
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "trading_platform.db")


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS signals_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                sector      TEXT    NOT NULL,
                signal_type TEXT    NOT NULL,
                confidence  INTEGER NOT NULL,
                score       INTEGER NOT NULL,
                entry_price REAL    NOT NULL,
                target      REAL    NOT NULL,
                stop_loss   REAL    NOT NULL,
                rr_ratio    REAL    NOT NULL DEFAULT 0,
                atr         REAL    NOT NULL DEFAULT 0,
                scanned_at  TEXT    NOT NULL,
                scan_type   TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'PENDING',
                exit_price  REAL,
                exit_at     TEXT,
                pnl_pct     REAL
            )
        """)
        
        # Self-healing migration for existing databases:
        # Check if columns exist and add them if missing
        cursor = c.cursor()
        cursor.execute("PRAGMA table_info(signals_history)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "rr_ratio" not in columns:
            try:
                c.execute("ALTER TABLE signals_history ADD COLUMN rr_ratio REAL NOT NULL DEFAULT 0")
            except Exception:
                pass
        if "atr" not in columns:
            try:
                c.execute("ALTER TABLE signals_history ADD COLUMN atr REAL NOT NULL DEFAULT 0")
            except Exception:
                pass
        c.commit()


def add_signal(sig: dict) -> Optional[int]:
    """
    Insert a new pending signal.
    If a PENDING signal already exists for this symbol in the same direction,
    skip (avoid duplicates). If direction reversed, close the old one first.
    Returns the new row id, or None if skipped.
    """
    with _conn() as c:
        # Check for existing pending signal for this symbol
        existing = c.execute(
            "SELECT id, signal_type FROM signals_history WHERE symbol=? AND status='PENDING'",
            (sig["symbol"],)
        ).fetchone()

        now = _now_ist()

        if existing:
            same_dir = (
                ("BUY" in existing["signal_type"]) == ("BUY" in sig["signal_type"])
            )
            if same_dir:
                return None  # Already tracking this direction
            # Opposite signal — close the old one
            c.execute(
                """UPDATE signals_history
                   SET status='CLOSED', exit_price=?, exit_at=?,
                       pnl_pct=?
                   WHERE id=?""",
                (
                    sig["entry_price"],
                    now,
                    _calc_pnl(existing["signal_type"], sig["entry_price"], sig["entry_price"]),
                    existing["id"],
                ),
            )

        cur = c.execute(
            """INSERT INTO signals_history
               (symbol, name, sector, signal_type, confidence, score,
                entry_price, target, stop_loss, rr_ratio, atr,
                scanned_at, scan_type)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sig["symbol"],
                sig.get("name", sig["symbol"]),
                sig.get("sector", "NSE"),
                sig["direction"],
                sig["confidence"],
                sig.get("bull_score", 0) if "BUY" in sig["direction"] else sig.get("bear_score", 0),
                sig["entry"],
                sig["target"],
                sig["stop_loss"],
                sig.get("rr_ratio", 0),
                sig.get("atr", 0),
                now,
                sig.get("scan_type", "INTRADAY"),
            ),
        )
        c.commit()
        return cur.lastrowid


def get_pending_signals() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM signals_history WHERE status='PENDING' ORDER BY scanned_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_signal(id: int, status: str, exit_price: float, pnl_pct: float):
    with _conn() as c:
        c.execute(
            """UPDATE signals_history
               SET status=?, exit_price=?, exit_at=?, pnl_pct=?
               WHERE id=?""",
            (status, exit_price, _now_ist(), pnl_pct, id),
        )
        c.commit()


def expire_old_intraday():
    """Mark intraday PENDING signals older than today as EXPIRED at 15:30 IST."""
    with _conn() as c:
        today = _now_ist()[:10]
        c.execute(
            """UPDATE signals_history
               SET status='EXPIRED', exit_at=?
               WHERE status='PENDING'
               AND scan_type='INTRADAY'
               AND scanned_at < ?""",
            (_now_ist(), today + " 00:00:00"),
        )
        c.commit()


def get_stats() -> dict:
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM signals_history").fetchone()[0]
        pending = c.execute(
            "SELECT COUNT(*) FROM signals_history WHERE status='PENDING'"
        ).fetchone()[0]
        won = c.execute(
            "SELECT COUNT(*) FROM signals_history WHERE status='HIT_TARGET'"
        ).fetchone()[0]
        lost = c.execute(
            "SELECT COUNT(*) FROM signals_history WHERE status='HIT_STOP'"
        ).fetchone()[0]
        expired = c.execute(
            "SELECT COUNT(*) FROM signals_history WHERE status='EXPIRED'"
        ).fetchone()[0]
        closed = c.execute(
            "SELECT COUNT(*) FROM signals_history WHERE status='CLOSED'"
        ).fetchone()[0]

        resolved = won + lost + closed + expired
        win_rate = round((won / resolved) * 100, 1) if resolved > 0 else 0

        avg_pnl_row = c.execute(
            "SELECT AVG(pnl_pct) FROM signals_history WHERE pnl_pct IS NOT NULL"
        ).fetchone()[0]
        avg_pnl = round(avg_pnl_row, 2) if avg_pnl_row else 0

        # By sector
        sector_rows = c.execute(
            """SELECT sector,
                      COUNT(*) as total,
                      SUM(CASE WHEN status='HIT_TARGET' THEN 1 ELSE 0 END) as wins
               FROM signals_history
               WHERE status IN ('HIT_TARGET','HIT_STOP','CLOSED','EXPIRED')
               GROUP BY sector"""
        ).fetchall()
        by_sector = [
            {
                "sector": r["sector"],
                "total": r["total"],
                "wins": r["wins"],
                "win_rate": round((r["wins"] / r["total"]) * 100, 1) if r["total"] > 0 else 0,
            }
            for r in sector_rows
        ]

        # By direction
        dir_rows = c.execute(
            """SELECT signal_type,
                      COUNT(*) as total,
                      SUM(CASE WHEN status='HIT_TARGET' THEN 1 ELSE 0 END) as wins,
                      AVG(pnl_pct) as avg_pnl
               FROM signals_history
               WHERE status IN ('HIT_TARGET','HIT_STOP','CLOSED','EXPIRED')
               GROUP BY CASE WHEN signal_type LIKE '%BUY%' THEN 'BUY' ELSE 'SELL' END"""
        ).fetchall()
        by_direction = [
            {
                "direction": "BUY" if "BUY" in r["signal_type"] else "SELL",
                "total": r["total"],
                "wins": r["wins"],
                "win_rate": round((r["wins"] / r["total"]) * 100, 1) if r["total"] > 0 else 0,
                "avg_pnl": round(r["avg_pnl"], 2) if r["avg_pnl"] else 0,
            }
            for r in dir_rows
        ]

        return {
            "total": total,
            "pending": pending,
            "won": won,
            "lost": lost,
            "expired": expired,
            "closed": closed,
            "resolved": resolved,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "by_sector": by_sector,
            "by_direction": by_direction,
        }


def get_history(limit: int = 100, symbol: str = None, status: str = None) -> list:
    with _conn() as c:
        q = "SELECT * FROM signals_history WHERE 1=1"
        params = []
        if symbol:
            q += " AND symbol=?"
            params.append(symbol)
        if status:
            q += " AND status=?"
            params.append(status)
        q += " ORDER BY scanned_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def clear_history():
    with _conn() as c:
        c.execute("DELETE FROM signals_history")
        c.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_ist() -> str:
    utc = datetime.now(timezone.utc)
    ist = utc + timedelta(hours=5, minutes=30)
    return ist.strftime("%Y-%m-%d %H:%M:%S")


def _calc_pnl(signal_type: str, entry: float, exit_price: float) -> float:
    if entry == 0:
        return 0.0
    if "BUY" in signal_type:
        return round(((exit_price - entry) / entry) * 100, 2)
    else:
        return round(((entry - exit_price) / entry) * 100, 2)
