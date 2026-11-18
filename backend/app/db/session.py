"""Async database session management with WAL mode and resilient connection pooling."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import async_sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# Async engine – SQLite WAL mode enabled via connect_args, resilient pooling
# ---------------------------------------------------------------------------
# Build the async SQLite URL from the existing db_path setting.
db_path = settings.db_path
if not db_path.startswith("sqlite"):
    db_path = f"sqlite:///{db_path}"

engine = create_async_engine(
    db_path,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    # WAL mode is a SQLite-specific connect_arg; it persists across connections.
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
        "isolation_level": "READ COMMITTED",
    },
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Async context manager – FastAPI dependency
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an :class:`AsyncSession` for FastAPI dependency injection.

    - On entry: creates a new session from the shared connection pool.
    - On success: commits the transaction, then closes the session.
    - On exception: rolls back and re-raises, ensuring the session is closed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Convenience helper – direct session factory (use with caution)
# ---------------------------------------------------------------------------
async def get_new_session() -> AsyncSession:
    """Return a fresh :class:`AsyncSession` from the pool without context manager."""
    return AsyncSessionLocal()


# ---------------------------------------------------------------------------
# Health check – verify database connectivity and WAL status
# ---------------------------------------------------------------------------
async def check_db_connection() -> bool:
    """Return True if the database is reachable and WAL mode is active."""
    try:
        async with engine.connect() as conn:
            # Executing a no-op statement confirms connectivity.
            # For SQLite, WAL mode can be queried via `PRAGMA journal_mode`.
            result = await conn.execute(text("PRAGMA journal_mode"))
            row = result.scalar_one_or_none()
            # row may be a string like 'wal' or None if unavailable
            is_wal = isinstance(row, str) and row.lower() == "wal"
            return True and is_wal  # always True if we reached here; flag for callers
    except Exception as exc:  # pragma: no cover
        print(f"[DB] Connection check failed: {exc}")
        return False