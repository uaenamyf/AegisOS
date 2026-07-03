from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    Pending = "pending"
    Running = "running"
    Succeeded = "succeeded"
    Failed = "failed"
    RolledBack = "rolled_back"
    Cancelled = "cancelled"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff: float = 1.5


@dataclass
class RollbackPlan:
    enabled: bool = False
    steps: list = field(default_factory=list)


@dataclass
class Task:
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
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    dag: dict = field(default_factory=dict)
    tasks: list = field(default_factory=list)


@dataclass
class Schedule:
    schedule_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    assigned_to: str = ""
    queued_at: float = 0.0
    priority: int = 0
