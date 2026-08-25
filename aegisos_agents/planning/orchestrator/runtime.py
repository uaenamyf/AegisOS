# date: 2026-07-06
# dev: myf
"""CyberRuntime —— 攻防场景运行时，实现 ``agents.api.RuntimeAPI``。

本模块提供 :class:`CyberRuntime`，作为 :class:`MockRuntime` 的替代实现。
内部委托 :class:`CyberOrchestrator` 的红蓝紫三条链，删除 MockRuntime 中
85 行手写 ``_cyber_dispatch_map()``。

调用契约：
    - ``run("red_chain", task)`` → ``CyberOrchestrator.run_red_chain(payload["target_range"])``
    - ``run("blue_chain", task)`` → ``CyberOrchestrator.run_blue_chain(payload["event_stream"])``
    - ``run("purple_review", task)`` → ``CyberOrchestrator.run_purple_review(chain, plan, alerts)``
    - 单个 ``agent_id``（如 ``"recon"``）→ 走通用 :class:`Orchestrator` + :class:`Planner`
      的单节点执行路径（不经过 CyberOrchestrator 的链式调用）

与 :class:`MockRuntime` 的关系：
    - :class:`MockRuntime` 保留作为向后兼容层（94 测试依赖其 dispatch map 行为）。
    - :class:`CyberRuntime` 是 R4.6 任务的产物，后续 ``backend/core/composition.py``
      的 DI 组合根可切换注入 :class:`CyberRuntime` 替代 :class:`MockRuntime`。
    - 两者实现相同的 ``RuntimeAPI`` Protocol（``submit`` / ``run`` / ``stop`` / ``heartbeat``）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from protocol import Heartbeat, NodeRef, Task, TaskStatus
from protocol.cyber import Alert, AttackChain, ResponsePlan


def _asdict(obj):
    return obj.model_dump() if isinstance(obj, BaseModel) else obj


class CyberRuntime:
    """攻防场景运行时 —— 委托 :class:`CyberOrchestrator` 执行红蓝紫链。

    实现 :class:`aegisos_agents.api.RuntimeAPI` Protocol。Mock 模式下注入
    :class:`MockProvider`，真实模式注入 SDK ``Model``。

    Attributes:
        _orchestrator: 内部持有的 :class:`CyberOrchestrator` 实例。
    """

    def __init__(self, mock: Any | None = None, model: Any | None = None) -> None:
        """初始化运行时，装配 CyberOrchestrator。

        Args:
            mock: :class:`MockProvider` 实例（Mock 模式）；真实模式传 None，
                由 CyberOrchestrator 内部根据环境变量决定。
            model: SDK ``Model`` 实例（真实 API 模式）；非 None 时优先于 mock，
                由 :meth:`SDKProvider.get_sdk_model` 创建。
        """
        self._orchestrator = CyberOrchestrator(mock=mock, model=model)

    def submit(self, task: Task) -> Task:
        """提交任务，标记为 Running 并填充占位 plan。

        Args:
            task: 待提交任务。

        Returns:
            状态更新为 :attr:`TaskStatus.Running` 的任务对象。
        """
        task.status = TaskStatus.Running
        task.plan = {"steps": ["plan", "route", "execute", "verify"]}
        return task

    def run(self, agent_id: str, task: Task) -> dict[str, Any]:
        """执行任务，按 agent_id 路由到 CyberOrchestrator 的对应链。

        Args:
            agent_id: 执行器标识，支持：
                - ``"red_chain"``：红队攻击链（recon→vuln→exploit）
                - ``"blue_chain"``：蓝队防御链（detector→triage→hunt→ir_planner）
                - ``"purple_review"``：紫队校验（critic + reviewer）
            task: 待执行任务，``task.plan`` 可含 ``target_range`` /
                ``event_stream`` / ``chain`` / ``plan`` / ``alerts`` 等输入。

        Returns:
            含 ``agent_id`` / ``task_id`` / ``status`` / ``output`` 的结果字典。
        """
        payload = getattr(task, "payload", None) or task.plan or {}

        if agent_id == "red_chain":
            target_range = payload.get("target_range", "10.0.0.0/24")
            output = self._orchestrator.run_red_chain(target_range)
            # protocol dataclass → dict 序列化（便于 backend JSON 响应）
            return self._wrap(agent_id, task.task_id, self._serialize_red(output))

        if agent_id == "blue_chain":
            event_stream = payload.get("event_stream", [])
            output = self._orchestrator.run_blue_chain(event_stream)
            return self._wrap(agent_id, task.task_id, self._serialize_blue(output))

        if agent_id == "purple_review":
            chain_data = payload.get("attack_chain", {})
            chain = (
                AttackChain.from_dict(chain_data) if isinstance(chain_data, dict)
                else chain_data
            )
            plan_data = payload.get("response_plan", {})
            plan = (
                ResponsePlan(**plan_data) if isinstance(plan_data, dict)
                else plan_data
            )
            alerts_data = payload.get("alerts", [])
            alerts = [
                Alert(**a) if isinstance(a, dict) else a
                for a in alerts_data
            ]
            output = self._orchestrator.run_purple_review(chain, plan, alerts)
            return self._wrap(agent_id, task.task_id, output)

        # 未知 agent_id：返回占位结果（与 MockRuntime 兼容）
        return self._wrap(agent_id, task.task_id, f"no handler for {agent_id}")

    def stop(self, agent_id: str) -> bool:
        """停止指定 Agent（当前实现总是成功）。"""
        return True

    def heartbeat(self, agent_id: str) -> Heartbeat:
        """返回指定 Agent 的心跳（标记为 healthy）。"""
        return Heartbeat(
            node=NodeRef(agent_id, "agent", agent_id),
            status="healthy",
        )

    @staticmethod
    def _wrap(agent_id: str, task_id: str, output: Any) -> dict[str, Any]:
        """包装执行结果为统一响应字典。"""
        return {
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "completed",
            "output": output,
        }

    @staticmethod
    def _serialize_red(result: dict) -> dict:
        """序列化红队链产出：dataclass 列表转 dict。"""
        return {
            "assets": [_asdict(a) for a in result["assets"]],
            "findings": [_asdict(f) for f in result["findings"]],
            "chain": result["chain"].to_dict(),
        }

    @staticmethod
    def _serialize_blue(result: dict) -> dict:
        """序列化蓝队链产出：dataclass 列表转 dict。"""
        return {
            "alerts": [_asdict(a) for a in result["alerts"]],
            "triaged": [_asdict(a) for a in result["triaged"]],
            "hypotheses": result["hypotheses"],
            "plan": _asdict(result["plan"]),
        }
