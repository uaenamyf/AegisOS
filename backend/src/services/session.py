# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 SessionService（实现 backend.api.SessionAPI）
from __future__ import annotations

import uuid
from typing import Any

from backend.src.mappers.converters import entity_to_session_dict
from backend.src.mappers.repositories import SessionRepository


class SessionService:
    """Implements ``backend.src.api.SessionAPI`` backed by ``SessionRepository``."""

    def __init__(self, repo: SessionRepository) -> None:
        self._repo = repo

    async def create_session(self, user_id: str) -> str:
        session_id = uuid.uuid4().hex
        await self._repo.create(session_id, user_id)
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        entity = await self._repo.get(session_id)
        if entity is None:
            return None
        return entity_to_session_dict(entity)

    async def close_session(self, session_id: str) -> bool:
        return await self._repo.update_status(session_id, "closed")
