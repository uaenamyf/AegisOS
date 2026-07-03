# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 端边云卸载调度
from __future__ import annotations

from dataclasses import dataclass, field

from protocol.scheduler import Task

EDGE_THRESHOLD = 5.0  # 秒


@dataclass
class Model:
    model_id: str
    tier: str = "cloud"  # edge | cloud
    size: str = "medium"  # small | medium | large
    capabilities: list = field(default_factory=list)


def schedule(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    """Decide which model (edge or cloud tier) to use for a given task.

    Rules:
    1. If task.privacy == "local", must pick edge tier.
    2. If task.latency_budget < EDGE_THRESHOLD, prefer edge.
    3. Otherwise prefer cloud (more capable).
    4. Filter by required_capability if given.
    """
    candidates = models
    if required_capability:
        candidates = [m for m in models if required_capability in m.capabilities]
    if not candidates:
        raise ValueError(f"No model with capability '{required_capability}'")

    if task.privacy == "local" or task.latency_budget < EDGE_THRESHOLD:
        edge = [m for m in candidates if m.tier == "edge"]
        if edge:
            return edge[0]
        return candidates[0]
    cloud = [m for m in candidates if m.tier == "cloud"]
    if cloud:
        return cloud[0]
    return candidates[0]
