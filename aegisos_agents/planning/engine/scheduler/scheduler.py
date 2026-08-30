# date: 2026-07-04
# dev: myf
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
DEVICE_THRESHOLD = 1.0  # 秒；低于此值必须端侧处理（超低延迟）
EDGE_THRESHOLD = 5.0  # 秒；低于此值优先边侧处理（低延迟）

# --- 层级偏好链（R2 修正：缺失层不再"取首个候选"，而是按语义显式降级）---
_ORDER_MOST_LOCAL = ("device", "edge", "cloud")  # 越靠前越贴近本地（隐私/超低延迟语义）
_ORDER_LOW_LATENCY = ("edge", "device", "cloud")  # 低延迟语义：端优于云
_ORDER_HEAVY = ("cloud", "edge", "device")  # 重活语义：越靠前算力越强


def _pick_by_preference(candidates: list[Model], order: tuple[str, ...]) -> Model:
    """按层级偏好顺序返回第一个命中者。

    Args:
        candidates: 非空候选列表。
        order: 三层层级偏好序列（必须覆盖 device/edge/cloud 全部取值）。

    Returns:
        命中的模型；order 覆盖全部层级时必命中，末位为防御性兜底。
    """
    for tier in order:
        for m in candidates:
            if m.tier == tier:
                return m
    return candidates[0]

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
    capabilities: list[str] = field(default_factory=list)


def schedule(
    task: Task,
    models: list[Model],
    required_capability: str | None = None,
) -> Model:
    """为给定任务选择执行模型（端侧/边侧/云侧层级）。

    五步调度策略（按优先级）：
        1. 能力过滤：若指定 required_capability，仅保留具备该能力的模型。
        2. 规则 1（隐私优先）：task.privacy == "local" 时必须选端侧，保障数据不出本地；
           无端侧时按"最贴近本地"降级（edge → cloud）。
        3. 规则 2（超低延迟）：latency_budget < DEVICE_THRESHOLD 依次选 device → edge，
           仅当二者皆缺才落云。
        4. 规则 3（低延迟）：latency_budget < EDGE_THRESHOLD 依次选 edge → device
           （端侧延迟天然低于云），仅当二者皆缺才落云。
        5. 规则 4（算力优先）：其余情况选 cloud，缺失时按算力降级 edge → device。

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

    # 规则 1: 隐私敏感 → 端侧，缺失按最本地降级
    if task.privacy == "local":
        return _pick_by_preference(candidates, _ORDER_MOST_LOCAL)

    # 规则 2: 超低延迟 → 端侧优先，边侧次之
    if task.latency_budget < DEVICE_THRESHOLD:
        return _pick_by_preference(candidates, _ORDER_MOST_LOCAL)

    # 规则 3: 低延迟 → 边侧优先（端侧延迟亦优于云）
    if task.latency_budget < EDGE_THRESHOLD:
        return _pick_by_preference(candidates, _ORDER_LOW_LATENCY)

    # 规则 4: 默认 → 云侧（算力最强），缺失按算力降级
    return _pick_by_preference(candidates, _ORDER_HEAVY)
