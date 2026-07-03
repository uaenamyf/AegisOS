# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 异构选举
from __future__ import annotations

from protocol.graph import GraphNode
from protocol.message import NodeRef


def elect(
    task_features: list[float],
    instances: list[GraphNode],
    capability_vectors: dict[str, list[float]],
) -> NodeRef:
    """Heterogeneous election: pick the instance whose capability vector
    has the highest dot-product with the task feature vector.
    """
    if not instances:
        return NodeRef(node_id="", node_type="agent")

    best_node = None
    best_score = float("-inf")

    for inst in instances:
        vec = capability_vectors.get(inst.node_id, [])
        score = sum(f * v for f, v in zip(task_features, vec))
        if score > best_score:
            best_score = score
            best_node = inst

    return NodeRef(
        node_id=best_node.node_id,
        node_type=best_node.kind.value,
    )
