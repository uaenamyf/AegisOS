# date: 2026-07-04
# dev: myf
"""数据库基础设施模块：提供异步 SQLAlchemy 引擎、会话工厂与初始化。"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.models.entities import Base
from tooling.configs.settings import settings

# 从统一配置读取默认数据库 URL
DEFAULT_DATABASE_URL = settings.database.url

# 全局会话工厂，由 configure_session_factory 注册，供 get_db 使用
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(url: str = DEFAULT_DATABASE_URL, echo: bool = False) -> AsyncEngine:
    """创建基于 aiosqlite 的异步 SQLAlchemy 引擎。

    Args:
        url: 数据库连接 URL，默认从统一配置读取。
        echo: 是否开启 SQL 回显日志，默认为 ``False``。

    Returns:
        异步引擎 ``AsyncEngine`` 实例。
    """
    return create_async_engine(url, echo=echo, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """创建绑定到指定引擎的异步会话工厂。

    Args:
        engine: 异步 SQLAlchemy 引擎实例。

    Returns:
        异步会话工厂 ``async_sessionmaker``。
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def configure_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    """注册全局会话工厂，供 ``get_db`` 依赖使用。

    Args:
        factory: 异步会话工厂实例。
    """
    global _session_factory
    _session_factory = factory


async def init_db(engine: AsyncEngine) -> None:
    """创建声明式基类上定义的所有数据库表。

    Args:
        engine: 异步 SQLAlchemy 引擎实例。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：生成一个异步数据库会话。

    Yields:
        异步数据库会话 ``AsyncSession``。

    Raises:
        RuntimeError: 全局会话工厂未配置时抛出。
    """
    if _session_factory is None:
        raise RuntimeError("Session factory not configured; call configure_session_factory first.")
    async with _session_factory() as session:
        try:
            yield session
        finally:
            await session.close()  # 确保会话资源释放
