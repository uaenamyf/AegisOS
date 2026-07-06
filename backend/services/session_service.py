# date: 2026-06-27
# dev: myf
"""Session 服务层：实现会话的创建、查询与关闭。"""

from __future__ import annotations

import uuid
from typing import Any

from backend.models.converters import entity_to_session_dict
from backend.repositories.repositories import SessionRepository


class SessionService:
    """实现 ``backend.api.SessionAPI``，底层委托 ``SessionRepository``。

    Attributes:
        _repo: 会话仓储，负责会话数据的持久化操作。
    """

    def __init__(self, repo: SessionRepository) -> None:
        self._repo = repo

    async def create_session(self, user_id: str) -> str:
        """创建新会话。

        Args:
            user_id: 发起会话的用户 ID。

        Returns:
            新创建的会话唯一标识符。
        """
        session_id = uuid.uuid4().hex  # 生成会话唯一 ID
        await self._repo.create(session_id, user_id)
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """获取指定会话的信息。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            会话信息字典；若会话不存在则返回 ``None``。
        """
        entity = await self._repo.get(session_id)
        if entity is None:
            return None
        return entity_to_session_dict(entity)

    async def close_session(self, session_id: str) -> bool:
        """关闭指定会话。

        Args:
            session_id: 会话唯一标识符。

        Returns:
            关闭成功返回 ``True``，否则返回 ``False``。
        """
        return await self._repo.update_status(session_id, "closed")
