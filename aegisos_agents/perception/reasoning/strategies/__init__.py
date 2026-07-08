# date: 2026-07-07
# dev: myf
# changelog: AP3 新增 GoalMode 导出--递归目标分解 + 失败重试 + 备选路径
"""推理策略包 -- Agent 行动范式（Plan / ReAct / Goal / Ask）。

AP1: :class:`PlanMode` -- 两阶段 LLM 推理（先规划策略，再按策略执行）。
AP3: :class:`GoalMode` -- 递归目标分解 + 失败重试 + 备选路径（跨 Agent 编排）。
后续 AP2/4 将在此包内新增 ReAct / Ask 范式。
"""
from .goal_mode import (
    GoalMode,
    GoalNode,
    GoalResult,
    GoalStatus,
    create_goal_mode_orchestrator,
)
from .plan_mode import (
    PlanMode,
    PlanResult,
    PlanStep,
    create_plan_mode_agent,
)

__all__ = [
    "GoalMode",
    "GoalNode",
    "GoalResult",
    "GoalStatus",
    "create_goal_mode_orchestrator",
    "PlanMode",
    "PlanResult",
    "PlanStep",
    "create_plan_mode_agent",
]
