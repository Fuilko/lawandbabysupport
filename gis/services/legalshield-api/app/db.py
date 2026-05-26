"""Async SQLAlchemy engine + session factory. PostGIS-aware via GeoAlchemy2.

Engine creation is **lazy** so that the GH Actions import smoke test can run
without installing the asyncpg driver. Engine + SessionFactory are built on
first use (FastAPI startup or first request).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


_engine: Optional[AsyncEngine] = None
_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _build() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    settings = get_settings()
    eng = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    fac = async_sessionmaker(eng, expire_on_commit=False, class_=AsyncSession)
    return eng, fac


def get_engine() -> AsyncEngine:
    global _engine, _factory
    if _engine is None:
        _engine, _factory = _build()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _factory
    if _factory is None:
        _engine, _factory = _build()
    return _factory


# Backwards-compatible attribute used in main.py
class _LazyEngineProxy:
    """Defers asyncpg import until first attribute access."""
    def __getattr__(self, item: str):
        return getattr(get_engine(), item)


engine = _LazyEngineProxy()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Convenience context manager for one-off scripts."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    async with get_session_factory()() as session:
        yield session
