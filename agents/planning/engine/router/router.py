# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 低熵稀疏路由 Top-K
from __future__ import annotations

from protocol.message import Message, NodeRef
from protocol.graph import Graph
from agents.planning.engine.topology.topology import active_subgraph

TOP_K = 3


def route(
    message: Message,
    topology: Graph,
    required_capability: str,
) -> list[NodeRef]:
    """Low-entropy sparse routing: return at most TOP_K best-matching
    NodeRefs, never broadcast to all capable nodes.
    """
    sub = active_subgraph(topology, required_capability)
    candidates = list(sub.nodes.values())
    scored = sorted(
        candidates,
        key=lambda n: _affinity(message, n) - _load_penalty(n),
        reverse=True,
    )
    k = min(TOP_K, len(scored))
    return [
        NodeRef(node_id=n.node_id, node_type=n.kind.value)
        for n in scored[:k]
    ]


def _affinity(message: Message, n) -> float:
    return getattr(n, "success_rate", 1.0)


def _load_penalty(n) -> float:
    return getattr(n, "latency", 0.0)
