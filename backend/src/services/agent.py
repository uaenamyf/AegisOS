# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 AgentService（list/get/invoke，委托 agents.api mock 实现）
from __future__ import annotations

from typing import Any

from agents.api import AgentRegistryAPI, RuntimeAPI
from protocol import Agent, Task


class AgentService:
    """Wraps ``AgentRegistryAPI`` + ``RuntimeAPI`` for agent-facing operations."""

    def __init__(self, registry: AgentRegistryAPI, runtime: RuntimeAPI) -> None:
        self._registry = registry
        self._runtime = runtime

    async def list_agents(self) -> list[Agent]:
        return self._registry.list_agents()

    async def get_agent(self, agent_id: str) -> Agent | None:
        try:
            return self._registry.get(agent_id)
        except KeyError:
            return None

    async def invoke(self, agent_id: str, goal: str, session_id: str = "") -> Any:
        task = Task(goal=goal)
        return self._runtime.run(agent_id, task)
