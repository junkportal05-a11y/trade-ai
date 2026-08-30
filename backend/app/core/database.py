"""Database layer with SQLAlchemy, connection pooling, and WAL mode."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

Base = declarative_base()

# ── Engine configuration ────────────────────────────────────────────────────
db_url = settings.database_url or ""

# Default to SQLite if no valid DATABASE_URL provided
if not db_url or db_url.startswith("sqlite"):
    db_uri = db_url if db_url and ":memory:" in db_url else f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', settings.db_path))}"
    if ":memory:" not in db_uri and "/" in db_uri:
        os.makedirs(os.path.dirname(db_uri.replace("sqlite:///", "")) or ".", exist_ok=True)
    engine = create_engine(
        db_uri,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=30000000000")
        cursor.close()

else:
    engine = create_engine(
        db_url,
        connect_args={"sslmode": "require"} if "supabase.com" in db_url or "sslmode=require" in db_url else {},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Dependency for FastAPI ──────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Synchronous context manager for DB access outside FastAPI deps."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Schema initialization (migrations) ────────────────────────────────────
def init_db() -> None:
    """Create tables if they don't exist."""
    from app.db import migrations
    migrations.run_migrations(engine)

    # Startup verification of WAL mode (only for SQLite)
    if (settings.database_url or "").startswith("sqlite"):
        try:
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA journal_mode;"))
                journal_mode = result.scalar()
            if journal_mode and journal_mode.lower() == "wal":
                logging.info("[startup] SQLite journal_mode verified: wal")
            else:
                logging.error(f"[startup] SQLite journal_mode is not WAL: {journal_mode}")
                raise RuntimeError("SQLite WAL mode failed to activate")
        except Exception as e:
            logging.error(f"[startup] Failed to verify SQLite WAL mode: {e}")
            raise RuntimeError("SQLite WAL mode failed to activate") from e