# date: 2026-07-04
# dev: myf
# changelog: 端边云三层卸载调度（device → edge → cloud）
"""端边云三层卸载调度器。

依据任务的隐私约束与延迟预算，在"端侧-边侧-云侧"三个层级中选择最合适的
模型执行任务，实现低延迟与强算力、本地隐私之间的权衡。

三层分级：
    - device: 端侧（PC/手机/IoT/防火墙盒子），超低延迟、完全本地隐私。
    - edge:   边侧（边缘网关/区县汇聚节点），中等算力、区域隔离。
    - cloud:  云侧（GPU 集群/厂家模型 API），强算力、可脱敏。

主要导出：
    - Model: 模型描述数据类。
    - schedule: 调度入口，按规则选定执行模型。
"""
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
    """可调度模型描述。

    Attributes:
        model_id: 模型唯一标识。
        tier: 所属层级，取值 device | edge | cloud。
        size: 模型规模，取值 small | medium | large，影响算力与资源占用。
        capabilities: 模型具备的能力标识列表，用于能力过滤。
    """

    model_id: str
    tier: str = "cloud"  # device | edge | cloud
    size: str = "medium"  # small | medium | large
    capabilities: list = field(default_factory=list)


def schedule(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    """为给定任务选择执行模型（端侧/边侧/云侧层级）。

    五步调度策略（按优先级）：
        1. 能力过滤：若指定 required_capability，仅保留具备该能力的模型。
        2. 规则 1（隐私优先）：task.privacy == "local" 时必须选端侧，保障数据不出本地；
           无端侧模型时降级为层级最低（延迟最小）的候选。
        3. 规则 2（超低延迟）：latency_budget < DEVICE_THRESHOLD 时优先端侧，
           端侧缺失则降级到边侧，再缺失取首个候选。
        4. 规则 3（低延迟）：latency_budget < EDGE_THRESHOLD 时优先边侧，
           边侧缺失取首个候选。
        5. 规则 4（算力优先）：其余情况选云侧，云侧缺失取首个候选。

    Args:
        task: 待调度任务，含隐私约束与延迟预算。
        models: 可用模型列表。
        required_capability: 可选，要求模型必须具备的能力标识。

    Returns:
        命中的最佳模型。

    Raises:
        ValueError: 能力过滤后无可用模型。
    """
    candidates = models
    # 步骤 1: 按能力过滤候选模型
    if required_capability:
        candidates = [m for m in models if required_capability in m.capabilities]
    if not candidates:
        raise ValueError(f"No model with capability '{required_capability}'")

    # 规则 1: 隐私敏感 → 端侧
    if task.privacy == "local":
        device = [m for m in candidates if m.tier == "device"]
        if device:
            return device[0]
        # 降级：无端侧模型时取层级最低（延迟最小）的候选
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
