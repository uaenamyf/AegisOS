# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建异步数据库引擎/会话工厂/init_db/get_db（aiosqlite）
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.mappers.entities import Base

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/aegisos.db"

_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(url: str = DEFAULT_DATABASE_URL, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine backed by aiosqlite."""
    return create_async_engine(url, echo=echo, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def configure_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    """Register the global session factory used by ``get_db``."""
    global _session_factory
    _session_factory = factory


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables defined on the declarative base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async DB session."""
    if _session_factory is None:
        raise RuntimeError("Session factory not configured; call configure_session_factory first.")
    async with _session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
