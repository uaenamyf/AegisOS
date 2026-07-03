# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 活跃子图计算
from __future__ import annotations

from protocol.graph import Graph, GraphNode

_ACTIVE_STATES = {"active", "degraded"}


def active_subgraph(graph: Graph, required_capability: str) -> Graph:
    """Return a sub-graph containing only nodes that:
    1. Are in an active or degraded state
    2. Possess the required capability
    """
    sub = Graph()
    for n in graph.nodes.values():
        status = getattr(n, "status", "active")
        if status in _ACTIVE_STATES and required_capability in n.capabilities:
            sub.add_node(n)
    return sub
