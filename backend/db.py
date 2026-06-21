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

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)
    load_dotenv(override=False)
except Exception:
    pass

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "trading_platform.db"))
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

    def executemany(self, query, params=None):
        self._lastrowid = None

        # Adapt SQL for PostgreSQL
        if IS_POSTGRES:
            query = query.replace("?", "%s")
            query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")

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

        # Execute query
        if params is not None:
            self.cursor_obj.executemany(query, params)
        else:
            self.cursor_obj.executemany(query)

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
                manual_override_reason  TEXT,
                setup_type              TEXT,
                market_regime_snapshot  TEXT,
                risk_amount             REAL,
                confidence_probability  REAL,
                r_multiple              REAL,
                exit_price              REAL,
                holding_time_minutes    REAL,
                pnl_pct                 REAL,
                pnl_inr                 REAL,
                resolution_reason       TEXT
            )
        """)

        # New tables for advanced metrics
        c.execute("""
            CREATE TABLE IF NOT EXISTS equity_curve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                equity_before REAL NOT NULL,
                equity_after REAL NOT NULL,
                peak_equity REAL NOT NULL,
                drawdown_pct REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS metrics_cache (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Phase Omega Tables
        c.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                current_equity REAL NOT NULL,
                peak_equity REAL NOT NULL,
                daily_equity REAL NOT NULL,
                sector_exposure TEXT NOT NULL,
                active_positions TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS strategy_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setup_type TEXT NOT NULL UNIQUE,
                lifetime_pf REAL NOT NULL,
                last_30_pf REAL NOT NULL,
                last_90_pf REAL NOT NULL,
                edge_score REAL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'ACTIVE'
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS confidence_calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                band TEXT NOT NULL,
                regime TEXT NOT NULL,
                predicted_win_rate REAL NOT NULL,
                actual_win_rate REAL NOT NULL,
                calibration_error REAL NOT NULL,
                UNIQUE(band, regime)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_governance_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT NOT NULL UNIQUE,
                pf REAL NOT NULL,
                ev REAL NOT NULL,
                drawdown REAL NOT NULL,
                regime TEXT NOT NULL,
                best_strategy TEXT,
                worst_strategy TEXT,
                calibration_error REAL,
                kill_switch_events INTEGER DEFAULT 0,
                exposure_violations INTEGER DEFAULT 0,
                data_confidence_score REAL DEFAULT 100.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS data_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                total_trades INTEGER,
                valid_trades INTEGER,
                confidence_score REAL,
                failures JSONB,
                locked BOOLEAN DEFAULT FALSE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS risk_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                daily_loss_limit REAL NOT NULL DEFAULT -3.0,
                daily_drawdown_limit REAL NOT NULL DEFAULT -4.0,
                max_consecutive_losses INTEGER NOT NULL DEFAULT 5,
                updated_at TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS rejected_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                rejection_category TEXT NOT NULL,
                rejection_reason TEXT NOT NULL,
                signal_price REAL,
                target_price REAL,
                stop_loss REAL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                scanned_at TEXT NOT NULL
            )
        """)

        c.commit()

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
                c.commit()
            except Exception:
                if IS_POSTGRES:
                    c.conn.rollback()
        if "atr" not in sig_columns:
            try:
                c.execute(
                    "ALTER TABLE signals_history ADD COLUMN atr REAL NOT NULL DEFAULT 0"
                )
                c.commit()
            except Exception:
                if IS_POSTGRES:
                    c.conn.rollback()

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
            ("manual_override_reason", "TEXT"),
            ("setup_type", "TEXT"),
            ("market_regime_snapshot", "TEXT"),
            ("risk_amount", "REAL"),
            ("confidence_probability", "REAL"),
            ("r_multiple", "REAL"),
            ("exit_price", "REAL"),
            ("holding_time_minutes", "REAL"),
            ("pnl_pct", "REAL"),
            ("pnl_inr", "REAL"),
            ("resolution_reason", "TEXT"),
            ("regime_score", "REAL"),
            ("sector_score", "REAL"),
            ("volume_score", "REAL"),
            ("news_score", "REAL"),
            ("rs_score", "REAL"),
            ("trade_quality_score", "REAL"),
            ("correlation_score", "REAL"),
            ("signal_time", "TEXT"),
            ("order_time", "TEXT"),
            ("fill_time", "TEXT"),
            ("fill_price", "REAL"),
            ("slippage_pct", "REAL"),
            ("broker_failure_reason", "TEXT"),
        ]
        for col_name, col_type in pred_migrations:
            if col_name not in pred_columns:
                try:
                    c.execute(f"ALTER TABLE predictions_history ADD COLUMN {col_name} {col_type}")
                    c.commit()
                except Exception:
                    if IS_POSTGRES:
                        c.conn.rollback()

        # Phase Omega: Add missing columns to strategy_health and daily_governance_reports
        try:
            sh_columns = [row["name"] for row in c.execute("PRAGMA table_info(strategy_health)").fetchall()]
            if "edge_score" not in sh_columns:
                c.execute("ALTER TABLE strategy_health ADD COLUMN edge_score REAL DEFAULT 0.0")
                c.commit()
        except Exception:
            if IS_POSTGRES:
                c.conn.rollback()

        try:
            dgr_columns = [row["name"] for row in c.execute("PRAGMA table_info(daily_governance_reports)").fetchall()]
            if "data_confidence_score" not in dgr_columns:
                c.execute("ALTER TABLE daily_governance_reports ADD COLUMN data_confidence_score REAL DEFAULT 100.0")
                c.commit()
            if "created_at" not in dgr_columns:
                c.execute("ALTER TABLE daily_governance_reports ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                c.commit()
        except Exception:
            if IS_POSTGRES:
                c.conn.rollback()
        
        # Initialize default risk settings if empty
        row = c.execute("SELECT COUNT(*) as count FROM risk_settings").fetchone()
        if row and row["count"] == 0:
            c.execute(
                "INSERT INTO risk_settings (daily_loss_limit, daily_drawdown_limit, max_consecutive_losses, updated_at) VALUES (?, ?, ?, ?)",
                (-3.0, -4.0, 5, _now_ist())
            )

        # Initialize portfolio state if empty
        p_row = c.execute("SELECT COUNT(*) as count FROM portfolio_state").fetchone()
        if p_row and p_row["count"] == 0:
            c.execute(
                "INSERT INTO portfolio_state (current_equity, peak_equity, daily_equity, sector_exposure, active_positions, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                (100000.0, 100000.0, 100000.0, "{}", "[]", _now_ist())
            )

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

def update_signals_batch(updates: list[tuple]):
    """Batch update multiple signals.
    updates should be a list of tuples: (status, exit_price, exit_at, pnl_pct, id)
    """
    if not updates:
        return
    with _conn() as c:
        c.executemany(
            """UPDATE signals_history
               SET status=?, exit_price=?, exit_at=?, pnl_pct=?
               WHERE id=?""",
            updates,
        )
        c.commit()

# Alias for compatibility with main.py references
update_signal_status = update_signal


def get_resolved_trades_for_validation(limit: int = 100) -> list:
    """Return recent resolved trades from prediction and signal history."""
    with _conn() as c:
        predictions = c.execute(
            """
            SELECT
                id,
                id as trade_id,
                symbol,
                prediction_type as direction,
                entry_price,
                target_price as target,
                stop_loss,
                prediction_date as created_at,
                resolved_at,
                exit_price,
                pnl_pct,
                status as result,
                market_regime_snapshot as regime,
                NULL as signal_id,
                'predictions_history' as source
            FROM predictions_history
            WHERE status NOT IN ('PENDING', 'ACTIVE')
            ORDER BY COALESCE(resolved_at, prediction_date) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        signals = c.execute(
            """
            SELECT
                id,
                id as trade_id,
                symbol,
                signal_type as direction,
                entry_price,
                target,
                stop_loss,
                scanned_at as created_at,
                exit_at as resolved_at,
                exit_price,
                pnl_pct,
                status as result,
                NULL as regime,
                id as signal_id,
                'signals_history' as source
            FROM signals_history
            WHERE status NOT IN ('PENDING', 'ACTIVE')
            ORDER BY COALESCE(exit_at, scanned_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        rows = [dict(row) for row in predictions] + [dict(row) for row in signals]

    rows.sort(key=lambda row: row.get("resolved_at") or row.get("created_at") or "", reverse=True)
    return rows[:limit]


def record_data_quality_check(result: dict) -> int:
    with _conn() as c:
        now = _now_ist()
        cur = c.execute(
            """
            INSERT INTO data_quality
                (checked_at, total_trades, valid_trades, confidence_score, failures, locked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                int(result.get("total_trades", 0)),
                int(result.get("valid_trades", 0)),
                float(result.get("confidence_score", 0.0)),
                json.dumps(result.get("failures", [])),
                bool(result.get("locked", True)),
            ),
        )
        c.commit()
        return cur.lastrowid


def get_latest_data_quality() -> Optional[dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM data_quality ORDER BY checked_at DESC, id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["failures"] = json.loads(result.get("failures") or "[]")
        except Exception:
            result["failures"] = []
        result["locked"] = bool(result.get("locked"))
        return result


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


def _get_stats_live() -> dict:
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

        cache = get_metrics_cache("dashboard_metrics") or {}
        
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
            "profit_factor": cache.get("profit_factor", 0.0),
            "ev_pct": cache.get("ev_pct", 0.0),
            "max_drawdown": cache.get("max_drawdown", 0.0),
            "avg_r": cache.get("avg_r", 0.0),
            "leaderboard": cache.get("leaderboard", [])
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
                market_breadth, sector_strength, nifty_trend, status, reason,
                setup_type, market_regime_snapshot, risk_amount, confidence_probability,
                regime_score, sector_score, volume_score, rs_score, trade_quality_score, correlation_score,
                signal_time, order_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pred["symbol"].upper(),
                pred.get("prediction_date", now),
                pred["prediction_type"].upper(),
                float(pred["entry_price"]),
                float(pred["target_price"]),
                float(pred["stop_loss"]),
                int(pred["confidence_score"]),
                float(pred["rsi"]),
                float(pred["macd"]),
                float(pred["adx"]),
                pred["sector"],
                float(pred["market_cap"]),
                float(pred["volume_ratio"]),
                float(pred["vwap_distance"]),
                float(pred.get("atr", 0.0)),
                float(pred.get("news_score", 0.0)),
                float(pred.get("market_breadth", 0.0)),
                float(pred.get("sector_strength", 0.0)),
                pred.get("nifty_trend", "FLAT"),
                pred.get("status", "PENDING"),
                pred.get("reason", ""),
                pred.get("setup_type", "UNKNOWN"),
                pred.get("market_regime_snapshot", "UNKNOWN"),
                float(pred.get("risk_amount", 0.0)),
                float(pred.get("confidence_probability", 0.5)),
                float(pred.get("regime_score", 0.0)),
                float(pred.get("sector_score", 0.0)),
                float(pred.get("volume_score", 0.0)),
                float(pred.get("rs_score", 0.0)),
                float(pred.get("trade_quality_score", 0.0)),
                float(pred.get("correlation_score", 0.0)),
                pred.get("signal_time", now),
                pred.get("order_time", now)
            ),
        )
        c.commit()
        return cur.lastrowid


def add_rejected_signal(sig: dict) -> int:
    with _conn() as c:
        now = _now_ist()
        cur = c.execute(
            """INSERT INTO rejected_signals 
               (symbol, rejection_category, rejection_reason, signal_price, target_price, stop_loss, status, scanned_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sig["symbol"].upper(),
                sig.get("rejection_category", "UNKNOWN"),
                sig.get("rejection_reason", ""),
                float(sig.get("signal_price", 0.0)),
                float(sig.get("target_price", 0.0)),
                float(sig.get("stop_loss", 0.0)),
                "PENDING",
                now
            ),
        )
        c.commit()
        return cur.lastrowid


def get_risk_settings() -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM risk_settings LIMIT 1").fetchone()
        if row:
            return dict(row)
        return {"daily_loss_limit": -3.0, "daily_drawdown_limit": -4.0, "max_consecutive_losses": 5}


def get_portfolio_state() -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM portfolio_state LIMIT 1").fetchone()
        if row:
            d = dict(row)
            try:
                d["sector_exposure"] = json.loads(d["sector_exposure"])
                d["active_positions"] = json.loads(d["active_positions"])
            except:
                d["sector_exposure"] = {}
                d["active_positions"] = []
            return d
        return {
            "current_equity": 100000.0,
            "peak_equity": 100000.0,
            "daily_equity": 100000.0,
            "sector_exposure": {},
            "active_positions": []
        }

def get_pending_rejected_signals() -> list:
    with _conn() as c:
        rows = c.execute("SELECT * FROM rejected_signals WHERE status='PENDING'").fetchall()
        return [dict(r) for r in rows]

def resolve_rejected_signal(sig_id: int, status: str):
    with _conn() as c:
        c.execute("UPDATE rejected_signals SET status=? WHERE id=?", (status, sig_id))
        c.commit()


def get_predictions() -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM predictions_history ORDER BY prediction_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_prediction(
    pred_id: int, 
    actual_outcome: float, 
    status: str, 
    exit_price: float = 0.0,
    holding_time_minutes: float = 0.0,
    pnl_pct: float = 0.0,
    pnl_inr: float = 0.0,
    r_multiple: float = 0.0,
    resolution_reason: str = "EXPIRED",
    fill_time: Optional[str] = None,
    slippage_pct: float = 0.0,
    broker_failure_reason: Optional[str] = None,
    manual_override_reason: Optional[str] = None
) -> bool:
    with _conn() as c:
        now = _now_ist()
        if fill_time is None:
            fill_time = now
            
        query = """UPDATE predictions_history 
                   SET actual_outcome=?, status=?, resolved_at=?,
                       exit_price=?, holding_time_minutes=?, pnl_pct=?, 
                       pnl_inr=?, r_multiple=?, resolution_reason=?,
                       fill_time=?, slippage_pct=?, broker_failure_reason=?
        """
        params = [
            actual_outcome, status.upper(), now,
            exit_price, holding_time_minutes, pnl_pct, pnl_inr, r_multiple, resolution_reason,
            fill_time, slippage_pct, broker_failure_reason
        ]
        
        if manual_override_reason:
            query += ", manual_override_reason=? WHERE id=?"
            params.extend([manual_override_reason, pred_id])
        else:
            query += " WHERE id=?"
            params.append(pred_id)
            
        cur = c.execute(query, tuple(params))
        c.commit()
        return cur.rowcount > 0


def add_equity_curve(trade_id: int, equity_before: float, equity_after: float, peak_equity: float, drawdown_pct: float) -> int:
    with _conn() as c:
        now = _now_ist()
        cur = c.execute(
            """INSERT INTO equity_curve 
               (trade_id, equity_before, equity_after, peak_equity, drawdown_pct, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (trade_id, equity_before, equity_after, peak_equity, drawdown_pct, now),
        )
        c.commit()
        return cur.lastrowid


def get_latest_equity() -> tuple:
    with _conn() as c:
        row = c.execute("SELECT equity_after, peak_equity FROM equity_curve ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            return float(row["equity_after"]), float(row["peak_equity"])
        # Default starting equity if none exists
        return 100000.0, 100000.0


def get_stats() -> dict:
    """Return stats from cache and append Phase Omega governance KPIs."""
    with _conn() as c:
        row = c.execute("SELECT value_json FROM metrics_cache WHERE key='stats_overview'").fetchone()
        stats = json.loads(row["value_json"]) if row else _get_stats_live()
        
        # Phase Omega Additions
        portfolio = get_portfolio_state()
        risk = get_risk_settings()
        
        gov_row = c.execute("SELECT * FROM daily_governance_reports ORDER BY report_date DESC LIMIT 1").fetchone()
        gov_report = dict(gov_row) if gov_row else {}
        
        # Determine Kill Switch Status
        daily_start = portfolio.get("daily_equity", 100000.0)
        current_eq = portfolio.get("current_equity", 100000.0)
        peak_eq = portfolio.get("peak_equity", 100000.0)
        
        daily_loss_pct = ((current_eq - daily_start) / daily_start) * 100 if daily_start else 0.0
        peak_dd_pct = ((current_eq - peak_eq) / peak_eq) * 100 if peak_eq else 0.0
        
        kill_switch_active = (daily_loss_pct <= risk["daily_loss_limit"]) or (peak_dd_pct <= risk["daily_drawdown_limit"])
        
        stats["portfolio"] = portfolio
        stats["governance"] = gov_report
        stats["kill_switch"] = "ACTIVE" if kill_switch_active else "SAFE"
        stats["current_regime"] = gov_report.get("regime", "UNKNOWN")
        stats["calibration_error"] = gov_report.get("calibration_error", 0.0)
        stats["strategy_health"] = gov_report.get("best_strategy", "N/A")
        
        return stats


def get_metrics_cache(key: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT value_json FROM metrics_cache WHERE key=?", (key,)).fetchone()
        if row:
            try:
                return json.loads(row["value_json"])
            except Exception:
                pass
        return None


def set_metrics_cache(key: str, data: dict):
    with _conn() as c:
        now = _now_ist()
        c.execute(
            """INSERT INTO metrics_cache (key, value_json, updated_at) 
               VALUES (?, ?, ?) 
               ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at""",
            (key, json.dumps(data), now)
        )
        c.commit()


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




def save_angelone_session(session_data: dict):
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
                "angelone_session",
                json.dumps(session_data),
                _now_ist(),
            ),
        )
        c.commit()


def get_angelone_session() -> Optional[dict]:
    try:
        with _conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
            )
            row = c.execute(
                "SELECT value FROM app_settings WHERE key='angelone_session'"
            ).fetchone()
            if row:
                return json.loads(row["value"])
    except Exception as e:
        import traceback
        print("Error in get_angelone_session:", e)
        traceback.print_exc()
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
