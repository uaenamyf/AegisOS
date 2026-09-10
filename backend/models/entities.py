# date: 2026-06-27
# dev: myf
"""ORM 实体模块：定义 SQLAlchemy 2.0 风格的声明式实体类。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 实体共享的声明式基类。"""


def _utcnow() -> datetime:
    """返回当前 UTC 时间，用作时间戳列的默认值。"""
    return datetime.now(UTC)


class SessionEntity(Base):
    """用户会话的持久化表示。

    Attributes:
        id: 会话唯一标识符（64 字符字符串）。
        user_id: 关联的用户 ID。
        status: 会话状态（active/closed 等）。
        context: 会话上下文数据，以 JSON 格式存储。
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC），每次更新自动刷新。
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )


class TaskEntity(Base):
    """计划任务的持久化表示。

    Attributes:
        id: 任务唯一标识符（64 字符字符串）。
        session_id: 所属会话 ID，建立索引以加速按会话查询。
        goal: 任务目标描述文本。
        payload: 任务执行输入数据，以 JSON 格式存储。
        status: 任务状态（pending/running/succeeded/failed 等）。
        plan: 任务执行计划，以 JSON 格式存储。
        result: 任务执行结果，以 JSON 格式存储。
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC），每次更新自动刷新。
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    dependency: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    priority: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )
