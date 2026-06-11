"""
db.py — Dynamic SQLite/PostgreSQL (Supabase) Database Adapter
===========================================================
Supports local SQLite fallback and remote PostgreSQL / Supabase in production.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "trading_platform.db")
DATABASE_URL = os.getenv("DATABASE_URL")
IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor


class RowWrapper:
    def __init__(self, data_dict, data_tuple):
        self.data_dict = data_dict
        self.data_tuple = data_tuple

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.data_tuple[key]
        return self.data_dict[key]

    def keys(self):
        return self.data_dict.keys()

    def get(self, key, default=None):
        return self.data_dict.get(key, default)

    def __iter__(self):
        return iter(self.data_dict)


class DBConnection:
    def __init__(self):
        self.conn = None
        self.cursor_obj = None
        self._lastrowid = None

    def __enter__(self):
        if IS_POSTGRES:
            self.conn = psycopg2.connect(DATABASE_URL)
            self.cursor_obj = self.conn.cursor(cursor_factory=RealDictCursor)
        else:
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor_obj = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.conn:
                self.conn.rollback()
        else:
            # commit will be called explicitly in write methods, but auto-commit on success is standard
            pass
        if self.cursor_obj:
            self.cursor_obj.close()
        if self.conn:
            self.conn.close()

    def commit(self):
        if self.conn:
            self.conn.commit()

    def cursor(self):
        return self

    def execute(self, query, params=None):
        self._lastrowid = None

        # Adapt SQL for PostgreSQL
        if IS_POSTGRES:
            query = query.replace("?", "%s")
            query = query.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
            )

            # Translate SQLite PRAGMA table_info to standard ANSI SQL
            if "PRAGMA table_info" in query:
                parts = query.split("table_info(")
                if len(parts) > 1:
                    tname = parts[1].replace(")", "").strip()
                    query = f"""
                        SELECT 0 as cid, column_name as name, data_type as type, 
                               CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END as notnull, 
                               column_default as dflt_value, 0 as pk 
                        FROM information_schema.columns 
                        WHERE table_name = '{tname}'
                    """

            # Translate SQLite INSERT OR REPLACE
            if "INSERT OR REPLACE INTO app_settings" in query:
                query = """
                    INSERT INTO app_settings (key, value, updated_at) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                """

            # Append RETURNING id to INSERT queries to get lastrowid
            stripped_upper = query.strip().upper()
            if (
                stripped_upper.startswith("INSERT INTO")
                and "RETURNING" not in stripped_upper
            ):
                if "APP_SETTINGS" not in stripped_upper:
                    query += " RETURNING id"

        # Execute query
        if params:
            self.cursor_obj.execute(query, params)
        else:
            self.cursor_obj.execute(query)

        # Retrieve last inserted ID if applicable
        if IS_POSTGRES:
            stripped_upper = query.strip().upper()
            if (
                stripped_upper.startswith("INSERT INTO")
                and "RETURNING ID" in stripped_upper
            ):
                try:
                    res = self.cursor_obj.fetchone()
                    if res:
                        if isinstance(res, dict):
                            self._lastrowid = res.get("id") or res.get("ID")
                        else:
                            self._lastrowid = res[0]
                except Exception:
                    pass
        else:
            self._lastrowid = self.cursor_obj.lastrowid

        return self

    def fetchall(self):
        rows = self.cursor_obj.fetchall()
        if IS_POSTGRES:
            return [RowWrapper(dict(r), tuple(r.values())) for r in rows]
        else:
            return rows

    def fetchone(self):
        row = self.cursor_obj.fetchone()
        if not row:
            return None
        if IS_POSTGRES:
            return RowWrapper(dict(row), tuple(row.values()))
        else:
            return row

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self.cursor_obj.rowcount


def _conn():
    return DBConnection()


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
        c.execute("""
            CREATE TABLE IF NOT EXISTS trade_journal (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT    NOT NULL,
                direction   TEXT    NOT NULL,
                entry_price REAL    NOT NULL,
                exit_price  REAL,
                qty         INTEGER NOT NULL,
                entry_date  TEXT    NOT NULL,
                reason      TEXT,
                emotion     TEXT,
                status      TEXT    NOT NULL DEFAULT 'OPEN',
                pnl         REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions_history (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol                  TEXT    NOT NULL,
                prediction_date         TEXT    NOT NULL,
                prediction_type         TEXT    NOT NULL,
                entry_price             REAL    NOT NULL,
                target_price            REAL    NOT NULL,
                stop_loss               REAL    NOT NULL,
                confidence_score        INTEGER NOT NULL,
                rsi                     REAL,
                macd                     REAL,
                adx                     REAL,
                sector                  TEXT,
                market_cap              REAL,
                volume_ratio            REAL,
                vwap_distance           REAL,
                atr                     REAL,
                news_score              REAL,
                market_breadth          REAL,
                sector_strength         REAL,
                nifty_trend             TEXT,
                actual_outcome          REAL,
                status                  TEXT    NOT NULL DEFAULT 'PENDING',
                reason                  TEXT,
                resolved_at             TEXT,
                manual_override_reason  TEXT
            )
        """)

        # Self-healing migration for existing databases:
        cursor = c.cursor()
        cursor.execute("PRAGMA table_info(signals_history)")
        columns = [row[1] for row in cursor.fetchall()]

        # Check signals_history
        cursor.execute("PRAGMA table_info(signals_history)")
        sig_columns = [row[1] for row in cursor.fetchall()]
        if "rr_ratio" not in sig_columns:
            try:
                c.execute(
                    "ALTER TABLE signals_history ADD COLUMN rr_ratio REAL NOT NULL DEFAULT 0"
                )
            except Exception:
                pass
        if "atr" not in sig_columns:
            try:
                c.execute(
                    "ALTER TABLE signals_history ADD COLUMN atr REAL NOT NULL DEFAULT 0"
                )
            except Exception:
                pass
                
        # Check predictions_history
        cursor.execute("PRAGMA table_info(predictions_history)")
        pred_columns = [row[1] for row in cursor.fetchall()]
        pred_migrations = [
            ("sector", "TEXT"),
            ("market_cap", "REAL"),
            ("volume_ratio", "REAL"),
            ("vwap_distance", "REAL"),
            ("atr", "REAL"),
            ("news_score", "REAL"),
            ("market_breadth", "REAL"),
            ("sector_strength", "REAL"),
            ("nifty_trend", "TEXT"),
            ("manual_override_reason", "TEXT")
        ]
        for col_name, col_type in pred_migrations:
            if col_name not in pred_columns:
                try:
                    c.execute(f"ALTER TABLE predictions_history ADD COLUMN {col_name} {col_type}")
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
            (sig["symbol"],),
        ).fetchone()

        now = _now_ist()

        if existing:
            same_dir = ("BUY" in existing["signal_type"]) == (
                "BUY" in sig["signal_type"]
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
                    _calc_pnl(
                        existing["signal_type"], sig["entry_price"], sig["entry_price"]
                    ),
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
                sig.get("bull_score", 0)
                if "BUY" in sig["direction"]
                else sig.get("bear_score", 0),
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


# Alias for compatibility with main.py references
update_signal_status = update_signal


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
                "win_rate": round((r["wins"] / r["total"]) * 100, 1)
                if r["total"] > 0
                else 0,
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
                "win_rate": round((r["wins"] / r["total"]) * 100, 1)
                if r["total"] > 0
                else 0,
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


def add_journal_entry(entry: dict) -> int:
    with _conn() as c:
        now = _now_ist()
        cur = c.execute(
            """INSERT INTO trade_journal 
               (symbol, direction, entry_price, exit_price, qty, entry_date, reason, emotion, status, pnl)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["symbol"].upper(),
                entry["direction"].upper(),
                float(entry["entry_price"]),
                float(entry["exit_price"]) if entry.get("exit_price") else None,
                int(entry["qty"]),
                entry.get("entry_date", now),
                entry.get("reason", ""),
                entry.get("emotion", "Calm"),
                entry.get("status", "OPEN"),
                float(entry["pnl"]) if entry.get("pnl") is not None else None,
            ),
        )
        c.commit()
        return cur.lastrowid


def get_journal_entries() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trade_journal ORDER BY entry_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_journal_entry(entry_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM trade_journal WHERE id=?", (entry_id,))
        c.commit()
        return cur.rowcount > 0


def add_prediction(pred: dict) -> int:
    with _conn() as c:
        now = _now_ist()
        cur = c.execute(
            """INSERT INTO predictions_history 
               (symbol, prediction_date, prediction_type, entry_price, target_price, stop_loss, confidence_score, 
                rsi, macd, adx, sector, market_cap, volume_ratio, vwap_distance, atr, news_score, 
                market_breadth, sector_strength, nifty_trend, status, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pred["symbol"].upper(),
                pred.get("prediction_date", now),
                pred["prediction_type"].upper(),
                float(pred["entry_price"]),
                float(pred["target_price"]),
                float(pred["stop_loss"]),
                int(pred["confidence_score"]),
                float(pred["rsi"]) if pred.get("rsi") is not None else None,
                float(pred["macd"]) if pred.get("macd") is not None else None,
                float(pred["adx"]) if pred.get("adx") is not None else None,
                pred.get("sector"),
                float(pred["market_cap"]) if pred.get("market_cap") is not None else None,
                float(pred["volume_ratio"]) if pred.get("volume_ratio") is not None else None,
                float(pred["vwap_distance"]) if pred.get("vwap_distance") is not None else None,
                float(pred["atr"]) if pred.get("atr") is not None else None,
                float(pred["news_score"]) if pred.get("news_score") is not None else None,
                float(pred["market_breadth"]) if pred.get("market_breadth") is not None else None,
                float(pred["sector_strength"]) if pred.get("sector_strength") is not None else None,
                pred.get("nifty_trend"),
                pred.get("status", "PENDING").upper(),
                pred.get("reason", ""),
            ),
        )
        c.commit()
        return cur.lastrowid


def get_predictions() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM predictions_history ORDER BY prediction_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_prediction(pred_id: int, actual_outcome: float, status: str, manual_override_reason: Optional[str] = None) -> bool:
    with _conn() as c:
        now = _now_ist()
        cur = c.execute(
            """UPDATE predictions_history 
               SET actual_outcome=?, status=?, resolved_at=? 
               WHERE id=?""",
            (actual_outcome, status.upper(), now, pred_id),
        )
        if manual_override_reason:
            cur = c.execute(
                """UPDATE predictions_history 
                   SET actual_outcome=?, status=?, resolved_at=?, manual_override_reason=? 
                   WHERE id=?""",
                (actual_outcome, status.upper(), now, manual_override_reason, pred_id)
            )
        else:
            cur = c.execute(
                """UPDATE predictions_history 
                   SET actual_outcome=?, status=?, resolved_at=? 
                   WHERE id=?""",
                (actual_outcome, status.upper(), now, pred_id)
            )
        c.commit()
        return cur.rowcount > 0


def delete_prediction(pred_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM predictions_history WHERE id=?", (pred_id,))
        c.commit()
        return cur.rowcount > 0


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


def save_upstox_token(token: str, raw: dict = None):
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        c.execute(
            """
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """,
            (
                "upstox_token",
                json.dumps({"access_token": token, **(raw or {})}),
                _now_ist(),
            ),
        )
        c.commit()


def get_upstox_token() -> Optional[str]:
    try:
        with _conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
            )
            row = c.execute(
                "SELECT value FROM app_settings WHERE key='upstox_token'"
            ).fetchone()
            if row:
                data = json.loads(row["value"])
                return data.get("access_token")
    except Exception:
        pass
    return None


def add_signals_batch(signals: list[dict]) -> None:
    """
    Batch insert new pending signals.
    Filters out duplicates or closes reversed signals just like add_signal,
    but executed in a single transaction for efficiency.
    """
    if not signals:
        return

    now = _now_ist()
    symbols = [sig["symbol"] for sig in signals]

    with _conn() as c:
        # 1. Fetch existing PENDING signals for the given symbols
        if IS_POSTGRES:
            placeholders = ",".join(["%s"] * len(symbols))
        else:
            placeholders = ",".join(["?"] * len(symbols))
        existing_rows = c.execute(
            f"SELECT id, symbol, signal_type, entry_price FROM signals_history WHERE status='PENDING' AND symbol IN ({placeholders})",
            symbols
        ).fetchall()

        existing_map = {r["symbol"]: r for r in existing_rows}

        insert_data = []
        update_data = []

        for sig in signals:
            symbol = sig["symbol"]
            existing = existing_map.get(symbol)

            if existing:
                same_dir = (
                    ("BUY" in existing["signal_type"]) == ("BUY" in sig.get("signal_type", sig.get("direction", "")))
                )
                if same_dir:
                    continue  # Already tracking this direction
                # Opposite signal — close the old one
                sig_entry_price = sig.get("entry_price", sig.get("entry", 0))
                pnl = _calc_pnl(existing["signal_type"], existing["entry_price"], sig_entry_price)
                update_data.append((
                    sig_entry_price,
                    now,
                    pnl,
                    existing["id"]
                ))

            # Prepare insertion
            insert_data.append((
                symbol,
                sig.get("name", symbol),
                sig.get("sector", "NSE"),
                sig["direction"],
                sig["confidence"],
                sig.get("bull_score", 0) if "BUY" in sig["direction"] else sig.get("bear_score", 0),
                sig.get("entry", 0),
                sig.get("target", 0),
                sig.get("stop_loss", 0),
                sig.get("rr_ratio", 0),
                sig.get("atr", 0),
                now,
                sig.get("scan_type", "INTRADAY"),
            ))

        # 2. Execute updates (closing opposite directions)
        if update_data:
            if IS_POSTGRES:
                update_query = """UPDATE signals_history
                   SET status='CLOSED', exit_price=%s, exit_at=%s,
                       pnl_pct=%s
                   WHERE id=%s"""
            else:
                update_query = """UPDATE signals_history
                   SET status='CLOSED', exit_price=?, exit_at=?,
                       pnl_pct=?
                   WHERE id=?"""

            c.cursor_obj.executemany(update_query, update_data)

        # 3. Execute inserts
        if insert_data:
            if IS_POSTGRES:
                query = """INSERT INTO signals_history
                   (symbol, name, sector, signal_type, confidence, score,
                    entry_price, target, stop_loss, rr_ratio, atr,
                    scanned_at, scan_type)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            else:
                query = """INSERT INTO signals_history
                   (symbol, name, sector, signal_type, confidence, score,
                    entry_price, target, stop_loss, rr_ratio, atr,
                    scanned_at, scan_type)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"""

            c.cursor_obj.executemany(query, insert_data)

        c.commit()
def get_pattern_hash(pred_dict: dict) -> str:
    """Generates a consistent pattern hash matching get_pattern_success_rates."""
    p_type = pred_dict.get("prediction_type", "BULLISH")
    rsi = pred_dict.get("rsi", 50)
    macd = pred_dict.get("macd", 0)
    
    rsi_bucket = "RSI_HIGH" if rsi > 60 else ("RSI_LOW" if rsi < 40 else "RSI_MID")
    macd_bucket = "MACD_POS" if macd > 0 else "MACD_NEG"
    
    return f"{p_type}_{rsi_bucket}_{macd_bucket}"

def get_pattern_success_rates() -> dict:
    """Returns win rates clustered by technical condition buckets."""
    try:
        with _conn() as c:
            rows = c.execute('''
                SELECT 
                    prediction_type,
                    CASE WHEN rsi > 60 THEN 'RSI_HIGH'
                         WHEN rsi < 40 THEN 'RSI_LOW'
                         ELSE 'RSI_MID' END as rsi_bucket,
                    CASE WHEN macd > 0 THEN 'MACD_POS' ELSE 'MACD_NEG' END as macd_bucket,
                    COUNT(*) as total,
                    SUM(CASE WHEN status IN ('WIN', 'CORRECT') THEN 1 ELSE 0 END) as wins
                FROM predictions_history
                WHERE status NOT IN ('PENDING', 'ACTIVE')
                GROUP BY prediction_type, rsi_bucket, macd_bucket
            ''').fetchall()
            
            results = {}
            for r in rows:
                if r["total"] > 0:
                    pattern = f"{r['prediction_type']}_{r['rsi_bucket']}_{r['macd_bucket']}"
                    results[pattern] = round((r["wins"] / r["total"]) * 100, 1)
            return results
    except Exception as e:
        return {}

def get_general_win_rate() -> float:
    """Returns the overall historical win rate."""
    try:
        with _conn() as c:
            total_row = c.execute("SELECT COUNT(*) FROM predictions_history WHERE status NOT IN ('PENDING', 'ACTIVE')").fetchone()
            total = total_row[0] if total_row else 0
            if total == 0: return 50.0
            
            wins_row = c.execute("SELECT COUNT(*) FROM predictions_history WHERE status IN ('WIN', 'CORRECT')").fetchone()
            wins = wins_row[0] if wins_row else 0
            return round((wins / total) * 100, 1)
    except Exception as e:
        return 50.0
