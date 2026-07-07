# date: 2026-07-07
# dev: myf
# changelog: AP1 新建 strategies 包——导出 PlanMode/PlanResult/PlanStep/create_plan_mode_agent
"""推理策略包 —— Agent 行动范式（Plan / ReAct / Goal / Ask）。

AP1: :class:`PlanMode` —— 两阶段 LLM 推理（先规划策略，再按策略执行）。
后续 AP2/3/4 将在此包内新增 ReAct / Goal / Ask 范式。
"""
from .plan_mode import (
    PlanMode,
    PlanResult,
    PlanStep,
    create_plan_mode_agent,
)

__all__ = [
    "PlanMode",
    "PlanResult",
    "PlanStep",
    "create_plan_mode_agent",
]
