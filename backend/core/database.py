"""
Async SQLAlchemy engine, session factory, and declarative base.

Usage in FastAPI routes:
    async def my_route(db: AsyncSession = Depends(get_db)): ...

Usage in Alembic:
    Import `sync_engine` for running migrations synchronously.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from backend.core.config import get_settings

settings = get_settings()

# ------------------------------------------------------------------ #
# Async engine (used by FastAPI, Celery tasks, etc.)
# ------------------------------------------------------------------ #
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ------------------------------------------------------------------ #
# Sync engine (used by Alembic only)
# ------------------------------------------------------------------ #
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# ------------------------------------------------------------------ #
# Declarative base shared by all models
# ------------------------------------------------------------------ #
Base = declarative_base()


# ------------------------------------------------------------------ #
# FastAPI dependency
# ------------------------------------------------------------------ #
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async database session.

    Commits on clean exit, rolls back on exception, and always closes
    the session when the request is finished.
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


# ------------------------------------------------------------------ #
# Table creation (development / testing convenience)
# ------------------------------------------------------------------ #
async def init_db() -> None:
    """Create all tables defined on ``Base``.

    In production, prefer running Alembic migrations instead of calling
    this function directly.
    """
    # Import all model modules so their classes are registered on ``Base``
    # before ``create_all`` is called.
    import backend.models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
