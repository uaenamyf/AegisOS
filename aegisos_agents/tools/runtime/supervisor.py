# date: 2026-08-03
# dev: 123 chen
"""运行时监督器 —— 多 Agent 生命周期托管。

在 :class:`AgentLifecycle` 状态机之上提供多 Agent 的
spawn / suspend / resume / kill 操作与统计查询。
"""

from __future__ import annotations

from aegisos_agents.tools.runtime.lifecycle import AgentLifecycle, AgentState


class RuntimeSupervisor:
    """多 Agent 运行时监督器。

    封装 :class:`AgentLifecycle`，提供批量 spawn/suspend/resume/kill
    与活跃/挂起 Agent 列表、统计信息查询。

    Attributes:
        _lifecycle: Agent 生命周期状态机。
    """

    def __init__(self) -> None:
        """初始化监督器，装配生命周期状态机。"""
        self._lifecycle = AgentLifecycle()

    # ---- Agent 操作 ----

    def spawn(self, agent_id: str, task_id: str) -> AgentState:
        """启动一个 Agent 实例。

        Args:
            agent_id: Agent 标识符。
            task_id: 关联任务标识符。

        Returns:
            新状态 RUNNING。
        """
        return self._lifecycle.start(agent_id, task_id)

    def suspend(self, agent_id: str, reason: str = "") -> AgentState:
        """挂起 Agent。

        Args:
            agent_id: Agent 标识符。
            reason: 挂起原因。

        Returns:
            新状态 SUSPENDED。
        """
        return self._lifecycle.suspend(agent_id, reason)

    def resume(self, agent_id: str) -> AgentState:
        """恢复挂起的 Agent。

        Args:
            agent_id: Agent 标识符。

        Returns:
            新状态 RUNNING。
        """
        return self._lifecycle.resume(agent_id)

    def kill(self, agent_id: str) -> AgentState:
        """强制终止 Agent（Running/Suspended → Failed）。

        Args:
            agent_id: Agent 标识符。

        Returns:
            新状态 FAILED。
        """
        return self._lifecycle.fail(agent_id, "killed by supervisor")

    def complete(self, agent_id: str, result: dict | None = None) -> AgentState:
        """标记 Agent 完成。

        Args:
            agent_id: Agent 标识符。
            result: 执行结果。

        Returns:
            新状态 COMPLETED。
        """
        return self._lifecycle.complete(agent_id, result)

    # ---- 监控 ----

    def heartbeat(self, agent_id: str):
        """触发 Agent 心跳（刷新最近心跳时间）。"""
        return self._lifecycle.heartbeat(agent_id)

    def check_timeout(self, agent_id: str, max_sec: float = 300.0) -> bool:
        """检查 Agent 是否超时。

        Args:
            agent_id: Agent 标识符。
            max_sec: 最大允许无心跳秒数，默认 300s。

        Returns:
            True 表示已超时。
        """
        return self._lifecycle.check_timeout(agent_id, max_sec)

    def status(self, agent_id: str) -> dict:
        """查询 Agent 状态。

        Args:
            agent_id: Agent 标识符。

        Returns:
            状态信息字典。
        """
        return self._lifecycle.status(agent_id)

    # ---- 列表查询 ----

    def list_active(self) -> list[str]:
        """列举所有活跃（RUNNING）Agent。

        Returns:
            agent_id 列表。
        """
        return self._filter_by_state(AgentState.RUNNING)

    def list_suspended(self) -> list[str]:
        """列举所有挂起（SUSPENDED）Agent。

        Returns:
            agent_id 列表。
        """
        return self._filter_by_state(AgentState.SUSPENDED)

    def list_completed(self) -> list[str]:
        """列举所有已完成 Agent。"""
        return self._filter_by_state(AgentState.COMPLETED)

    def list_failed(self) -> list[str]:
        """列举所有失败 Agent。"""
        return self._filter_by_state(AgentState.FAILED)

    # ---- 统计 ----

    def stats(self) -> dict:
        """聚合统计所有 Agent 状态分布。

        Returns:
            含 active/suspended/completed/failed/timeout/total 数量的字典。
        """
        counts: dict[str, int] = {}
        for rec in self._lifecycle._records.values():
            key = rec.state.value
            counts[key] = counts.get(key, 0) + 1
        return {
            "active": counts.get("running", 0),
            "suspended": counts.get("suspended", 0),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "timeout": counts.get("timeout", 0),
            "total": len(self._lifecycle._records),
        }

    # ---- 私有 ----

    def _filter_by_state(self, state: AgentState) -> list[str]:
        """按状态过滤 Agent ID 列表。

        Args:
            state: 目标状态。

        Returns:
            匹配的 agent_id 列表。
        """
        return [
            aid
            for aid, rec in self._lifecycle._records.items()
            if rec.state == state
        ]
