"""调度协议类型。

定义任务调度相关的数据契约，包括任务状态、重试策略、回滚计划、
任务、计划与调度记录，是 AegisOS 任务编排的核心类型层。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举。

    表示任务在生命周期中的当前阶段。
    """

    Pending = "pending"        # 待执行：已创建尚未开始
    Running = "running"        # 执行中：正在被 Agent 处理
    Succeeded = "succeeded"    # 成功：任务正常完成
    Failed = "failed"         # 失败：执行出错（可重试或回滚）
    RolledBack = "rolled_back"  # 已回滚：失败后已执行回滚
    Cancelled = "cancelled"   # 已取消：被主动取消


@dataclass
class RetryPolicy:
    """重试策略。

    定义任务失败后的重试行为。

    Attributes:
        max_attempts: 最大尝试次数（含首次）。
        backoff: 退避乘数，每次重试等待时间为上次的 backoff 倍。
    """

    max_attempts: int = 3
    backoff: float = 1.5


@dataclass
class RollbackPlan:
    """回滚计划。

    定义任务失败后恢复状态的步骤。

    Attributes:
        enabled: 是否启用回滚。
        steps: 回滚步骤列表。
    """

    enabled: bool = False
    steps: list = field(default_factory=list)


@dataclass
class Task:
    """任务。

    描述一个待执行的调度单元，包含目标、计划、状态与执行策略。

    Attributes:
        task_id: 任务唯一标识，自动生成 UUID hex。
        goal: 任务目标描述。
        plan: 执行计划详情。
        status: 当前任务状态，参见 TaskStatus。
        retry: 重试策略。
        rollback: 回滚计划。
        dependency: 依赖的任务 ID 列表，需完成后才能执行。
        priority: 优先级，数值越大越优先。
        privacy: 隐私级别：local / standard / unrestricted。
        latency_budget: 延迟预算（秒），超时视为失败。
    """

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    plan: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.Pending
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    rollback: RollbackPlan = field(default_factory=RollbackPlan)
    dependency: list = field(default_factory=list)
    priority: int = 0
    privacy: str = "standard"  # local | standard | unrestricted
    latency_budget: float = 10.0  # 秒


@dataclass
class Plan:
    """执行计划。

    描述一组任务的编排方式，通常以 DAG 形式组织。

    Attributes:
        plan_id: 计划唯一标识，自动生成 UUID hex。
        goal: 计划总体目标。
        dag: 任务依赖的有向无环图描述。
        tasks: 包含的 Task 列表。
    """

    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    dag: dict = field(default_factory=dict)
    tasks: list = field(default_factory=list)


@dataclass
class Schedule:
    """调度记录。

    描述一个任务被分配到 Agent 的调度信息。

    Attributes:
        schedule_id: 调度记录唯一标识，自动生成 UUID hex。
        task_id: 被调度的任务 ID。
        assigned_to: 被分配的 Agent ID。
        queued_at: 入队时间（Unix 时间戳，秒）。
        priority: 调度优先级。
    """

    schedule_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    assigned_to: str = ""
    queued_at: float = 0.0
    priority: int = 0
