# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 端边云三层卸载调度（device → edge → cloud）
from __future__ import annotations

from dataclasses import dataclass, field

from protocol.scheduler import Task

# --- 三层延迟阈值 ---
DEVICE_THRESHOLD = 1.0   # 秒；低于此值必须端侧处理（超低延迟）
EDGE_THRESHOLD = 5.0    # 秒；低于此值优先边侧处理（低延迟）

# --- 三层 tier 定义 ---
# device: 端侧（PC/手机/IoT/防火墙盒子）— 超低延迟、完全本地隐私
# edge:   边侧（边缘网关/机架服务器/区县汇聚节点）— 中等算力、区域隔离
# cloud:  云侧（GPU 集群/厂家模型 API）— 强算力、可脱敏


@dataclass
class Model:
    model_id: str
    tier: str = "cloud"  # device | edge | cloud
    size: str = "medium"  # small | medium | large
    capabilities: list = field(default_factory=list)


def schedule(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    """Decide which model (device / edge / cloud tier) to use for a given task.

    Three-tier scheduling rules:
    1. If task.privacy == "local", must pick device tier (完全本地隐私).
    2. If task.latency_budget < DEVICE_THRESHOLD, prefer device (超低延迟).
    3. If task.latency_budget < EDGE_THRESHOLD, prefer edge (低延迟).
    4. Otherwise prefer cloud (more capable).
    5. Filter by required_capability if given.
    """
    candidates = models
    if required_capability:
        candidates = [m for m in models if required_capability in m.capabilities]
    if not candidates:
        raise ValueError(f"No model with capability '{required_capability}'")

    # 规则 1: 隐私敏感 → 端侧
    if task.privacy == "local":
        device = [m for m in candidates if m.tier == "device"]
        if device:
            return device[0]
        # 降级：无端侧模型时取延迟最低的
        return sorted(candidates, key=lambda m: {"device": 0, "edge": 1, "cloud": 2}[m.tier])[0]

    # 规则 2: 超低延迟 → 端侧
    if task.latency_budget < DEVICE_THRESHOLD:
        device = [m for m in candidates if m.tier == "device"]
        if device:
            return device[0]
        # 降级到边侧
        edge = [m for m in candidates if m.tier == "edge"]
        if edge:
            return edge[0]
        return candidates[0]

    # 规则 3: 低延迟 → 边侧
    if task.latency_budget < EDGE_THRESHOLD:
        edge = [m for m in candidates if m.tier == "edge"]
        if edge:
            return edge[0]
        return candidates[0]

    # 规则 4: 默认 → 云侧（算力最强）
    cloud = [m for m in candidates if m.tier == "cloud"]
    if cloud:
        return cloud[0]
    return candidates[0]
