# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 AgentService（list/get/invoke，委托 agents.api mock 实现）
"""Agent 服务层：封装 agent 注册中心与运行时，提供面向 agent 的操作。"""

from __future__ import annotations

from typing import Any

from agents.api import AgentRegistryAPI, RuntimeAPI
from protocol import Agent, Task


class AgentService:
    """封装 ``AgentRegistryAPI`` 与 ``RuntimeAPI``，提供面向 agent 的操作。

    Attributes:
        _registry: agent 注册中心 API，负责 agent 元数据的查询。
        _runtime: agent 运行时 API，负责实际执行任务。
    """

    def __init__(self, registry: AgentRegistryAPI, runtime: RuntimeAPI) -> None:
        self._registry = registry
        self._runtime = runtime

    async def list_agents(self) -> list[Agent]:
        """列出所有已注册的 agent。

        Returns:
            已注册 agent 列表。
        """
        return self._registry.list_agents()

    async def get_agent(self, agent_id: str) -> Agent | None:
        """根据 agent ID 获取 agent 信息。

        Args:
            agent_id: agent 的唯一标识符。

        Returns:
            匹配到的 ``Agent`` 对象；若不存在则返回 ``None``。
        """
        try:
            return self._registry.get(agent_id)
        except KeyError:
            return None

    async def invoke(self, agent_id: str, goal: str, session_id: str = "") -> Any:
        """调用指定 agent 执行目标。

        Args:
            agent_id: 目标 agent 的唯一标识符。
            goal: 任务目标描述。
            session_id: 会话 ID，用于关联执行上下文，默认为空字符串。

        Returns:
            agent 运行时返回的执行结果。
        """
        task = Task(goal=goal)
        return self._runtime.run(agent_id, task)

