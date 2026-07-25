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
if settings.is_postgres:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )
else:
    # SQLite with WAL mode for safe multi-threaded access
    db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", settings.db_path)
    )
    os.makedirs(os.path.dirname(db_path) if "/" in db_path else ".", exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=30000000000")
        cursor.close()


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
    if not settings.is_postgres:
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