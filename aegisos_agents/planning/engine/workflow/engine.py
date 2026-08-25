# date: 2026-07-06
# dev: myf
"""DAG 工作流引擎 —— 节点编排、状态机推进、条件分支、并行汇聚。

本模块实现 :class:`WorkflowEngine`，接收有向无环图（DAG）描述的工作流，
按依赖关系拓扑排序后执行节点。无依赖的节点并行执行，依赖完成的节点
按顺序触发，支持条件分支跳过与失败传播。

设计要点：
    - **DAG 表示**：``{node_id: WorkflowNode}``，节点 ``dependencies`` 列出
      前驱节点 ID。``executor`` 是 ``Callable[[dict], dict]``，接收上游
      产出字典，返回自身产出。
    - **拓扑排序**：Kahn 算法（入度表 + 队列），执行前先检测循环依赖。
    - **并行汇聚**：同层无依赖节点用 ``ThreadPoolExecutor`` 并行执行。
    - **条件分支**：节点 ``condition`` 为可选谓词 ``Callable[[dict], bool]``，
      返回 False 则跳过该节点（状态 Skipped），其下游仍可执行（条件失败
      不传播为依赖失败）。
    - **状态机**：Pending → Running → Succeeded / Failed / Skipped。
    - **失败传播**：节点 Failed 时，其下游节点标记为 Skipped（不执行）。

与现有架构的关系：
    - 输入 ``dag`` 字段对齐 :class:`protocol.scheduler.Plan.dag`（dict 结构）。
    - 与 :class:`EventBus` 集成：节点执行前后发布 ``AgentStart``/``AgentFinish``。
    - 不引入新依赖（``concurrent.futures`` 为标准库）。
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from protocol.event import Event, EventType
from protocol.message import NodeRef


class WorkflowStatus(StrEnum):
    """工作流节点状态枚举。

    表示节点在执行过程中的当前阶段，由 :class:`WorkflowEngine` 推进。
    """

    Pending = "pending"      # 待执行：尚未轮到（依赖未完成）
    Running = "running"      # 执行中：正在调用 executor
    Succeeded = "succeeded"  # 成功：executor 正常返回
    Failed = "failed"        # 失败：executor 抛异常
    Skipped = "skipped"      # 跳过：条件不满足 或 上游失败


@dataclass
class WorkflowNode:
    """工作流节点描述。

    每个节点对应一个执行单元，``executor`` 接收上游产出字典并返回自身产出。
    ``condition`` 可选，用于条件分支（返回 False 时跳过本节点）。

    Attributes:
        node_id: 节点唯一标识。
        executor: 执行函数，签名 ``executor(upstream_outputs: dict) -> Any``，
            其中 ``upstream_outputs`` 是 ``{dep_node_id: dep_output}``。
        dependencies: 前驱节点 ID 列表，全部成功后本节点才执行。
        condition: 可选条件谓词，签名 ``condition(upstream_outputs: dict) -> bool``，
            返回 False 时跳过本节点（状态 Skipped）。None 表示无条件执行。
        name: 节点可读名称，用于日志与事件。
    """

    node_id: str
    executor: Callable[[dict], Any]
    dependencies: list[str] = field(default_factory=list)
    condition: Callable[[dict], bool] | None = None
    name: str = ""


@dataclass
class WorkflowResult:
    """工作流执行结果。

    记录每个节点的最终状态与产出，以及整体执行是否成功。

    Attributes:
        node_statuses: node_id -> :class:`WorkflowStatus`。
        node_outputs: node_id -> executor 返回值（Skipped/Failed 节点无）。
        errors: node_id -> 异常描述（仅 Failed 节点）。
        success: 整体是否成功（所有非 Skipped 节点均 Succeeded）。
    """

    node_statuses: dict[str, WorkflowStatus] = field(default_factory=dict)
    node_outputs: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    success: bool = True


class WorkflowEngine:
    """DAG 工作流引擎 —— 拓扑排序 + 并行执行 + 状态机推进。

    引擎本身无状态，每次 :meth:`run` 独立计算结果。可选注入 :class:`EventBus`
    在节点执行前后发布事件，供可观测层消费。
    """

    def __init__(self, eventbus: Any | None = None) -> None:
        """初始化工作流引擎。

        Args:
            eventbus: 可选的 :class:`EventBus` 实例；注入后节点执行前后
                会发布 ``AgentStart``/``AgentFinish`` 事件。None 表示不发布。
        """
        self._eventbus = eventbus

    def run(
        self,
        nodes: dict[str, WorkflowNode],
        context: dict | None = None,
        task_id: str = "",
        max_workers: int = 4,
    ) -> WorkflowResult:
        """执行一个 DAG 工作流。

        流程：
            1. 拓扑排序（Kahn 算法），检测循环依赖。
            2. 按层执行：同层无依赖节点并行，等待全部完成后进入下一层。
            3. 每节点：检查上游状态 → 条件判断 → 执行/跳过 → 发布事件。
            4. 失败传播：Failed 节点的下游标记 Skipped。

        Args:
            nodes: node_id -> :class:`WorkflowNode`。
            context: 可选的初始上下文，会合并到上游产出中传给 executor。
            task_id: 关联任务 ID，用于事件发布。
            max_workers: 并行执行线程数上限。

        Returns:
            :class:`WorkflowResult`，含每节点状态与产出。

        Raises:
            ValueError: DAG 存在循环依赖。
        """
        # 1. 拓扑排序（同时验证无环）
        order = self._topological_sort(nodes)

        # 2. 初始化状态
        result = WorkflowResult()
        for node_id in nodes:
            result.node_statuses[node_id] = WorkflowStatus.Pending
        # 累计产出：节点产出 + 初始 context（供下游读取）
        accumulated: dict[str, Any] = dict(context or {})
        # context 快照：传给每个 executor 的 upstream 基底（只读）
        context_snapshot = dict(context or {})

        # 3. 按拓扑层执行（同层并行）
        for layer in order:
            # 筛选本层可执行节点：依赖全完成 + 状态仍 Pending
            ready: list[str] = []
            for node_id in layer:
                node = nodes[node_id]
                deps_ok = all(
                    result.node_statuses.get(dep) == WorkflowStatus.Succeeded
                    for dep in node.dependencies
                )
                # 上游有 Failed/Skipped → 本节点跳过（失败传播）
                deps_failed = any(
                    result.node_statuses.get(dep)
                    in (WorkflowStatus.Failed, WorkflowStatus.Skipped)
                    for dep in node.dependencies
                )
                if deps_failed:
                    result.node_statuses[node_id] = WorkflowStatus.Skipped
                elif deps_ok:
                    ready.append(node_id)
                # 否则保持 Pending（下一层再判）

            if not ready:
                continue

            # 并行执行本层就绪节点
            self._execute_layer(
                nodes, ready, accumulated, context_snapshot,
                result, task_id, max_workers
            )

        # 4. 汇总成功标志：所有非 Skipped 节点均 Succeeded
        result.success = all(
            status in (WorkflowStatus.Succeeded, WorkflowStatus.Skipped)
            for status in result.node_statuses.values()
        ) and any(
            status == WorkflowStatus.Succeeded
            for status in result.node_statuses.values()
        )
        return result

    def _topological_sort(
        self, nodes: dict[str, WorkflowNode]
    ) -> list[list[str]]:
        """Kahn 拓扑排序，返回分层结果（每层可并行）。

        Args:
            nodes: 节点字典。

        Returns:
            层列表，每层是 node_id 列表。同层节点互不依赖，可并行执行。

        Raises:
            ValueError: 检测到循环依赖（剩余节点入度均非零）。
        """
        # 入度表：节点未处理依赖数
        in_degree: dict[str, int] = {
            nid: len(node.dependencies) for nid, node in nodes.items()
        }
        # 反向邻接表：dep -> 依赖它的节点列表
        dependents: dict[str, list[str]] = {nid: [] for nid in nodes}
        for nid, node in nodes.items():
            for dep in node.dependencies:
                # 依赖项不存在时跳过（外部 context 依赖）
                if dep in dependents:
                    dependents[dep].append(nid)

        layers: list[list[str]] = []
        # 初始零入度节点
        current_layer = [nid for nid, deg in in_degree.items() if deg == 0]

        processed = 0
        while current_layer:
            layers.append(current_layer)
            next_layer: list[str] = []
            for nid in current_layer:
                # 消费该节点：其下游入度 -1
                for dependent in dependents[nid]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_layer.append(dependent)
                processed += 1
            current_layer = next_layer

        # 循环依赖检测：有节点入度仍非零
        if processed != len(nodes):
            remaining = [
                nid for nid, deg in in_degree.items() if deg > 0
            ]
            raise ValueError(
                f"Cycle detected in DAG; unresolved nodes: {remaining}"
            )
        return layers

    def _execute_layer(
        self,
        nodes: dict[str, WorkflowNode],
        ready: list[str],
        accumulated: dict[str, Any],
        context_snapshot: dict[str, Any],
        result: WorkflowResult,
        task_id: str,
        max_workers: int,
    ) -> None:
        """并行执行一层就绪节点。

        单层节点数 ≤ max_workers 时直接并行；超出则分批。每个节点执行
        前后发布事件（若注入了 eventbus），产出回写到 ``accumulated``。
        """
        # 单节点无需线程池开销
        if len(ready) == 1:
            self._execute_node(
                nodes[ready[0]], accumulated, context_snapshot, result, task_id
            )
            return

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(
                    self._execute_node,
                    nodes[nid], accumulated, context_snapshot, result, task_id
                ): nid
                for nid in ready
            }
            for fut in as_completed(futures):
                # 异常已在 _execute_node 内捕获并记入 result
                fut.result()

    def _execute_node(
        self,
        node: WorkflowNode,
        accumulated: dict[str, Any],
        context_snapshot: dict[str, Any],
        result: WorkflowResult,
        task_id: str,
    ) -> None:
        """执行单个节点：状态机推进 + 条件判断 + 事件发布。

        流程：Pending → Running → 条件检查 →（执行/Skipped）→ Succeeded/Failed。
        产出回写到 ``accumulated[node.node_id]`` 供下游读取。upstream 字典
        以 context 为基底，合并 dependencies 的产出。
        """
        result.node_statuses[node.node_id] = WorkflowStatus.Running
        self._emit(
            EventType.AgentStart, node, task_id,
            payload={"phase": "start"},
        )

        # upstream = context（只读基底）+ 上游节点产出
        upstream: dict[str, Any] = dict(context_snapshot)
        for dep in node.dependencies:
            upstream[dep] = accumulated.get(dep)

        # 条件分支：condition 返回 False → 跳过
        if node.condition is not None:
            try:
                if not node.condition(upstream):
                    result.node_statuses[node.node_id] = WorkflowStatus.Skipped
                    self._emit(
                        EventType.AgentFinish, node, task_id,
                        payload={"phase": "skipped"},
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                # condition 抛异常视为节点失败
                result.node_statuses[node.node_id] = WorkflowStatus.Failed
                result.errors[node.node_id] = f"condition error: {exc!r}"
                self._emit(
                    EventType.AgentFinish, node, task_id,
                    payload={"phase": "failed", "error": repr(exc)},
                )
                return

        # 执行 executor
        try:
            output = node.executor(upstream)
            result.node_outputs[node.node_id] = output
            accumulated[node.node_id] = output
            result.node_statuses[node.node_id] = WorkflowStatus.Succeeded
            self._emit(
                EventType.AgentFinish, node, task_id,
                payload={"phase": "succeeded"},
            )
        except Exception as exc:  # noqa: BLE001 - 引擎必须隔离节点异常
            result.node_statuses[node.node_id] = WorkflowStatus.Failed
            result.errors[node.node_id] = repr(exc)
            self._emit(
                EventType.AgentFinish, node, task_id,
                payload={"phase": "failed", "error": repr(exc)},
            )

    def _emit(
        self,
        event_type: EventType,
        node: WorkflowNode,
        task_id: str,
        payload: dict,
    ) -> None:
        """向事件总线发布节点生命周期事件（若注入了 eventbus）。"""
        if self._eventbus is None:
            return
        event = Event(
            event_type=event_type,
            task_id=task_id,
            source=NodeRef(node.node_id, "workflow_node", node.name or node.node_id),
            payload=payload,
        )
        self._eventbus.publish(event)
