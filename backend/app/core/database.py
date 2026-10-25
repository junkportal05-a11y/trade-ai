"""Database layer with SQLAlchemy, connection pooling, and WAL mode."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

Base = declarative_base()

# ── Engine configuration ────────────────────────────────────────────────────
# Force SQLite if DATABASE_URL is missing, empty, or unparseable — prevents
# uvicorn crash when env var is unset (e.g. Hugging Face Space without secret).
db_url = (settings.database_url or "").strip()


def _normalize_postgres_url(url: str) -> str:
    """Normalize PostgreSQL URL to use psycopg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _create_sqlite_engine() -> Engine:
    db_path = getattr(settings, "db_path", "../trading_platform.db")
    db_uri = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', db_path))}"
    if "/" in db_uri.replace("sqlite:///", "") or "\\" in db_uri.replace("sqlite:///", ""):
        os.makedirs(os.path.dirname(db_uri.replace("sqlite:///", "")) or ".", exist_ok=True)
    eng = create_engine(
        db_uri,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=30000000000")
        cursor.close()
    return eng


def _create_postgres_engine(url: str) -> Engine:
    """Create production-grade PostgreSQL engine with optimized connection pooling."""
    normalized_url = _normalize_postgres_url(url)
    return create_engine(
        normalized_url,
        connect_args={"sslmode": "require"} if "supabase.com" in url or "sslmode=require" in url else {},
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300,
    )


def _create_engine() -> Engine:
    """Create database engine with automatic fallback to SQLite."""
    if not db_url:
        logging.info("[db] No DATABASE_URL configured — using SQLite fallback")
        return _create_sqlite_engine()

    # Validate URL parseability
    try:
        from sqlalchemy.engine.url import make_url as _make_url
        _ = _make_url(db_url)
    except Exception:
        logging.info("[db] Invalid DATABASE_URL — using SQLite fallback")
        return _create_sqlite_engine()

    # Try PostgreSQL
    try:
        engine = _create_postgres_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logging.info("[db] PostgreSQL connection verified")
        return engine
    except OperationalError as e:
        logging.info(f"[db] PostgreSQL connection failed ({e}), falling back to SQLite")
        return _create_sqlite_engine()


engine = _create_engine()

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


def get_pool_status() -> dict:
    """Get connection pool status for health checks."""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }


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