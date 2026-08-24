# date: 2026-07-07
# dev: myf
# changelog: AP3 新增 GoalMode 导出--递归目标分解 + 失败重试 + 备选路径
# changelog: AP4.1 新增 AskMode/AskHandler/MockAskHandler/AutoAskHandler/AskRequest/AskResponse 导出
"""推理策略包 -- Agent 行动范式（Plan / ReAct / Goal / Ask）。

AP1: :class:`PlanMode` -- 两阶段 LLM 推理（先规划策略，再按策略执行）。
AP2.1: :class:`ReactMode` -- 可追溯的 think→act→observe 工具调用循环。
AP3: :class:`GoalMode` -- 递归目标分解 + 失败重试 + 备选路径（跨 Agent 编排）。
AP4: :class:`AskMode` -- 人机协同（暂停提问 + 超时降级）。
后续 AP2 将在此包内新增 ReAct 范式。
"""
from .ask_mode import (
    AskHandler,
    AskMode,
    AskRequest,
    AskResponse,
    AskTimeoutError,
    AutoAskHandler,
    MockAskHandler,
    severity_at_least,
)
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

# date: 2026-08-12
# dev: overwhelmingly
# changelog: 导出 AP2.1 ReAct 循环及其决策、轨迹和结果类型
from .react_mode import (
    ReactDecision,
    ReactDecisionKind,
    ReactExecutor,
    ReactMode,
    ReactResult,
    ReactStatus,
    ReactStep,
    ReactThinker,
)

__all__ = [
    "AskHandler",
    "AskMode",
    "AskRequest",
    "AskResponse",
    "AskTimeoutError",
    "AutoAskHandler",
    "MockAskHandler",
    "severity_at_least",
    "GoalMode",
    "GoalNode",
    "GoalResult",
    "GoalStatus",
    "create_goal_mode_orchestrator",
    "PlanMode",
    "PlanResult",
    "PlanStep",
    "create_plan_mode_agent",
    "ReactDecision",
    "ReactDecisionKind",
    "ReactExecutor",
    "ReactMode",
    "ReactResult",
    "ReactStatus",
    "ReactStep",
    "ReactThinker",
]
