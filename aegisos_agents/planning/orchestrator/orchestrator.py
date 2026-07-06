# date: 2026-07-06
# dev: myf
# changelog: 新建通用 Orchestrator——整合 Planner + WorkflowEngine + EventBus，将 Plan 转 WorkflowNode 执行
"""通用编排器 —— 整合 Planner + WorkflowEngine + EventBus。

本模块实现 :class:`Orchestrator`，将规划-执行闭环串联：
    1. :class:`Planner` 将 goal 分解为 :class:`protocol.Plan`（DAG + tasks）。
    2. 本模块将 ``Plan.dag`` 转换为 ``WorkflowNode`` 字典，每个节点的
       ``executor`` 调用注入的 ``runtime.run(agent_id, task)``。
    3. :class:`WorkflowEngine` 按拓扑序并行执行，产出汇聚。
    4. :class:`EventBus` 发布节点生命周期事件（AgentStart/AgentFinish），
       供 ``observability/inspect/`` 消费。

与 :class:`CyberOrchestrator` 的关系：
    - :class:`CyberOrchestrator` 是 SDK 专用的攻防编排器（手动 _run() 串联
      11 个 SDK Agent，对应 R4.2 handoffs 待深化）。
    - :class:`Orchestrator`（本类）是通用编排器，基于 Plan + WorkflowEngine，
      可接入任意 :class:`RuntimeAPI` 实现（MockRuntime / CyberRuntime / 真实 runtime）。
    - 两者互补：CyberOrchestrator 适合 SDK 原生 handoffs 链；
      本类适合通用 DAG（含条件分支、并行汇聚）。
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from protocol.scheduler import Plan, Task
from aegisos_agents.planning.engine.eventbus import EventBus
from aegisos_agents.planning.engine.workflow import (
    WorkflowEngine,
    WorkflowNode,
    WorkflowResult,
    WorkflowStatus,
)
from aegisos_agents.planning.planner import Planner


class _RuntimeLike(Protocol):
    """编排器所需的运行时接口（与 :class:`aegisos_agents.api.RuntimeAPI` 对齐）。

    只依赖 ``run`` 方法，避免强制要求完整 RuntimeAPI。
    """

    def run(self, agent_id: str, task: Task) -> Any: ...


class Orchestrator:
    """通用编排器 —— Planner + WorkflowEngine + EventBus 整合。

    将 goal 分解为 Plan，转换为 WorkflowNode 后由 WorkflowEngine 执行，
    全程通过 EventBus 发布事件。编排器本身无状态，每次 :meth:`execute`
    独立运行。

    Attributes:
        _planner: 任务规划器实例。
        _engine: 工作流引擎实例。
        _eventbus: 事件总线实例（可能为 None）。
    """

    def __init__(
        self,
        planner: Planner | None = None,
        engine: WorkflowEngine | None = None,
        eventbus: EventBus | None = None,
    ) -> None:
        """初始化编排器。

        Args:
            planner: 任务规划器；None 时用默认 :class:`Planner`。
            engine: 工作流引擎；None 时新建（若提供 eventbus 则注入）。
            eventbus: 事件总线；None 时不发布事件。注入后会传给 engine。
        """
        self._planner = planner or Planner()
        self._eventbus = eventbus
        if engine is None:
            self._engine = WorkflowEngine(eventbus=eventbus)
        else:
            self._engine = engine

    def execute(
        self,
        goal: str,
        runtime: _RuntimeLike,
        scenario: str | None = None,
        context: dict | None = None,
    ) -> WorkflowResult:
        """一站式编排：goal -> Plan -> WorkflowNode -> 执行。

        Args:
            goal: 高层目标描述。
            runtime: 运行时实现（需提供 ``run(agent_id, task)``）。
            scenario: 场景模板名；None 用 planner 默认。
            context: 初始上下文（如 ``{"target_range": "10.0.0.0/24"}``），
                会合并到上游产出传给 executor。

        Returns:
            :class:`WorkflowResult`，含每节点状态与产出。
        """
        plan = self._planner.plan(goal, scenario=scenario)
        return self.execute_plan(plan, runtime, context=context)

    def execute_plan(
        self,
        plan: Plan,
        runtime: _RuntimeLike,
        context: dict | None = None,
    ) -> WorkflowResult:
        """执行一个已构造好的 Plan。

        将 ``plan.dag`` 的每个 node_id 转换为 :class:`WorkflowNode`，
        executor 调用 ``runtime.run(node_id, task)``。node_id 与 task 的
        对应关系按 ``plan.dag`` 的 key 顺序与 ``plan.tasks`` 顺序对齐
        （:class:`Planner` 保证两者同序）。

        Args:
            plan: 已构造的计划（含 dag 与 tasks）。
            runtime: 运行时实现。
            context: 初始上下文。

        Returns:
            :class:`WorkflowResult`。

        Raises:
            ValueError: plan.dag 与 plan.tasks 数量不一致。
        """
        node_ids = list(plan.dag.keys())
        if len(node_ids) != len(plan.tasks):
            raise ValueError(
                f"Plan dag nodes ({len(node_ids)}) != tasks ({len(plan.tasks)})"
            )

        # 把 task_id -> node_id 映射建好，便于 executor 从 upstream 取值
        task_by_node: dict[str, Task] = {}
        for node_id, task in zip(node_ids, plan.tasks):
            task_by_node[node_id] = task

        # 构造 WorkflowNode 字典
        nodes: dict[str, WorkflowNode] = {}
        for node_id in node_ids:
            task = task_by_node[node_id]
            deps = plan.dag[node_id]
            nodes[node_id] = WorkflowNode(
                node_id=node_id,
                executor=self._make_executor(node_id, task, runtime),
                dependencies=deps,
                name=node_id,
            )

        return self._engine.run(
            nodes,
            context=context,
            task_id=plan.plan_id,
        )

    @staticmethod
    def _make_executor(
        node_id: str,
        task: Task,
        runtime: _RuntimeLike,
    ) -> Callable[[dict], Any]:
        """构造节点执行函数：调用 runtime.run(node_id, task)。

        executor 接收 upstream 产出字典，将其作为 ``task.plan`` 注入
        （供 runtime 读取上游产出），然后调用 runtime.run。
        """

        def _exec(upstream: dict) -> Any:
            # 把上游产出注入 task.plan，runtime 可从中读取前驱结果
            task.plan = {"upstream": dict(upstream)}
            return runtime.run(node_id, task)

        return _exec

    @property
    def eventbus(self) -> EventBus | None:
        """当前注入的事件总线（可能为 None）。"""
        return self._eventbus
