# date: 2026-08-03
# dev: 123 chen
"""Agent 生命周期状态机 —— 状态转换 + 心跳 + 超时检测。

实现 Agent 六态状态机：Init → Running ⇌ Suspended → Completed/Failed/Timeout。
复用 ``protocol/heartbeat.py`` 的 Heartbeat 类型。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from protocol.heartbeat import Heartbeat
from protocol.message import NodeRef


class AgentState(StrEnum):
    """Agent 生命周期状态枚举。"""

    INIT = "init"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# 合法状态转换表
_VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.INIT: {AgentState.RUNNING},
    AgentState.RUNNING: {AgentState.SUSPENDED, AgentState.COMPLETED, AgentState.FAILED, AgentState.TIMEOUT},
    AgentState.SUSPENDED: {AgentState.RUNNING, AgentState.FAILED},
    AgentState.COMPLETED: set(),
    AgentState.FAILED: set(),
    AgentState.TIMEOUT: set(),
}


@dataclass
class AgentRecord:
    """Agent 生命周期记录。

    Attributes:
        agent_id: Agent 标识符。
        task_id: 关联任务标识符。
        state: 当前状态。
        started_at: 启动时间戳（monotonic）。
        last_heartbeat: 最近心跳时间戳。
        error: 失败原因（仅 FAILED 状态）。
        result: 执行结果（仅 COMPLETED 状态）。
    """

    agent_id: str = ""
    task_id: str = ""
    state: AgentState = AgentState.INIT
    started_at: float = 0.0
    last_heartbeat: float = 0.0
    suspend_reason: str = ""
    error: str = ""
    result: dict | None = None


class AgentLifecycle:
    """Agent 生命周期管理器。

    管理单个 Agent 的六态状态机（Init→Running⇌Suspended→Completed/Failed/Timeout），
    提供心跳检测与超时判定。

    Attributes:
        _records: {agent_id -> AgentRecord} 生命周期记录表。
    """

    def __init__(self) -> None:
        """初始化空的生命周期管理器。"""
        self._records: dict[str, AgentRecord] = {}

    # ---- 状态转换 ----

    def start(self, agent_id: str, task_id: str) -> AgentState:
        """启动 Agent：Init → Running。

        Args:
            agent_id: Agent 标识符。
            task_id: 关联任务标识符。

        Returns:
            新状态 RUNNING。
        """
        self._records[agent_id] = AgentRecord(
            agent_id=agent_id,
            task_id=task_id,
            state=AgentState.RUNNING,
            started_at=time.monotonic(),
            last_heartbeat=time.monotonic(),
        )
        return AgentState.RUNNING

    def suspend(self, agent_id: str, reason: str = "") -> AgentState:
        """挂起 Agent：Running → Suspended。

        Args:
            agent_id: Agent 标识符。
            reason: 挂起原因。

        Returns:
            新状态 SUSPENDED。

        Raises:
            KeyError: agent_id 不存在。
            ValueError: 状态转换非法（如已完成/失败后挂起）。
        """
        rec = self._records[agent_id]
        self._check_transition(rec.state, AgentState.SUSPENDED)
        rec.state = AgentState.SUSPENDED
        rec.suspend_reason = reason
        return AgentState.SUSPENDED

    def resume(self, agent_id: str) -> AgentState:
        """恢复 Agent：Suspended → Running。

        Args:
            agent_id: Agent 标识符。

        Returns:
            新状态 RUNNING。
        """
        rec = self._records[agent_id]
        self._check_transition(rec.state, AgentState.RUNNING)
        rec.state = AgentState.RUNNING
        rec.last_heartbeat = time.monotonic()
        rec.suspend_reason = ""
        return AgentState.RUNNING

    def complete(self, agent_id: str, result: dict | None = None) -> AgentState:
        """标记完成：Running → Completed。

        Args:
            agent_id: Agent 标识符。
            result: 执行结果字典。

        Returns:
            新状态 COMPLETED。
        """
        rec = self._records[agent_id]
        self._check_transition(rec.state, AgentState.COMPLETED)
        rec.state = AgentState.COMPLETED
        rec.result = result
        rec.last_heartbeat = time.monotonic()
        return AgentState.COMPLETED

    def fail(self, agent_id: str, error: str = "") -> AgentState:
        """标记失败：Running/Suspended → Failed。

        Args:
            agent_id: Agent 标识符。
            error: 失败原因。

        Returns:
            新状态 FAILED。
        """
        rec = self._records[agent_id]
        self._check_transition(rec.state, AgentState.FAILED)
        rec.state = AgentState.FAILED
        rec.error = error
        rec.last_heartbeat = time.monotonic()
        return AgentState.FAILED

    # ---- 心跳 ----

    def heartbeat(self, agent_id: str) -> Heartbeat:
        """返回 Agent 心跳并刷新最近心跳时间。

        Args:
            agent_id: Agent 标识符。

        Returns:
            Heartbeat 对象。

        Raises:
            KeyError: agent_id 不存在。
        """
        rec = self._records[agent_id]
        rec.last_heartbeat = time.monotonic()
        return Heartbeat(
            node=NodeRef(agent_id, "agent", agent_id),
            status=rec.state.value,
        )

    def check_timeout(self, agent_id: str, max_sec: float) -> bool:
        """检查是否超时（最近心跳距今超过 max_sec）。

        Args:
            agent_id: Agent 标识符。
            max_sec: 最大允许无心跳秒数。

        Returns:
            True 表示已超时。

        Raises:
            KeyError: agent_id 不存在。
        """
        rec = self._records[agent_id]
        if rec.state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.TIMEOUT):
            return False
        elapsed = time.monotonic() - rec.last_heartbeat
        if elapsed > max_sec:
            self._check_transition(rec.state, AgentState.TIMEOUT)
            rec.state = AgentState.TIMEOUT
            rec.error = f"heartbeat timeout: {elapsed:.1f}s > {max_sec}s"
            return True
        return False

    # ---- 查询 ----

    def status(self, agent_id: str) -> dict:
        """查询 Agent 当前状态。

        Args:
            agent_id: Agent 标识符。

        Returns:
            含 agent_id / task_id / state / uptime / error 的字典。
        """
        rec = self._records.get(agent_id)
        if rec is None:
            return {"agent_id": agent_id, "state": "unknown"}
        uptime = time.monotonic() - rec.started_at if rec.started_at > 0 else 0.0
        return {
            "agent_id": rec.agent_id,
            "task_id": rec.task_id,
            "state": rec.state.value,
            "uptime": round(uptime, 2),
            "error": rec.error,
            "suspend_reason": rec.suspend_reason,
        }

    # ---- 私有 ----

    @staticmethod
    def _check_transition(current: AgentState, target: AgentState) -> None:
        """校验状态转换合法性。

        Args:
            current: 当前状态。
            target: 目标状态。

        Raises:
            ValueError: 当转换非法时。
        """
        valid = _VALID_TRANSITIONS.get(current, set())
        if target not in valid:
            raise ValueError(
                f"状态转换非法: {current.value} → {target.value}"
            )
