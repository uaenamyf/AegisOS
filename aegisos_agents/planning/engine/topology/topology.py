# date: 2026-07-04
# dev: myf
"""活跃子图拓扑模块。

从全局拓扑图中筛选出当前可参与任务执行的节点子集，作为路由与调度的前置过滤。
仅保留状态正常且具备所需能力的节点，避免将任务分发给离线或无能力的节点。

主要导出：
    - active_subgraph: 依据能力与状态裁剪出活跃子图。
"""

from __future__ import annotations

from protocol.graph import Graph

# 节点可参与调度的状态集合：active=正常, degraded=降级但仍可用
_ACTIVE_STATES = {"active", "degraded"}


def active_subgraph(graph: Graph, required_capability: str) -> Graph:
    """返回仅包含活跃且具备指定能力节点的子图。

    过滤条件：
        1. 节点状态属于 _ACTIVE_STATES（active / degraded）。
        2. 节点能力列表中包含 required_capability。

    Args:
        graph: 完整节点拓扑图。
        required_capability: 子图节点必须具备的能力标识。

    Returns:
        新的 Graph 实例，仅含满足条件的节点；无匹配时为空图。
    """
    sub = Graph()
    for n in graph.nodes.values():
        # 缺省状态视为 active，保证未显式设置状态的节点可被调度
        status = getattr(n, "status", "active")
        if status in _ACTIVE_STATES and required_capability in n.capabilities:
            sub.add_node(n)
    return sub
