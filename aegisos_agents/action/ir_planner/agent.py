# date: 2026-07-06
# dev: myf
# changelog: AP1.3 接入 Plan 范式——新增 plan_response_with_strategy 方法
"""蓝队响应规划 Agent 模块（SDK 结构化输出版 + Plan 范式）。

AP1.3 新增：``plan_response_with_strategy`` 方法用 :class:`PlanMode` 两阶段推理，
先规划多阶段响应策略（隔离→阻断→诱饵→监控），再按策略生成详细 DefenseAction 列表。
原有 ``plan_response`` 方法保持不变（向后兼容）。
"""
from __future__ import annotations

import json

from aegisos_agents.action.output_types import IRPlannerResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import PlanMode
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import ResponsePlan

SYSTEM_PROMPT = (
    "You are an incident response planner. Given threat hypotheses, "
    "return JSON with plan_id, actions (array of {action_id, kind "
    "isolate|block|decoy|monitor, target, rationale}), confidence (float), "
    "rollback (dict with enabled and steps)."
)


class IRPlannerAgent(StructuredAgent[IRPlannerResult], PlanMode[IRPlannerResult]):
    """蓝队响应规划 Agent（SDK 结构化输出 + Plan 范式）。

    AP1.3：``plan_response_with_strategy`` 用 :class:`PlanMode` 两阶段推理，
    先规划多阶段响应策略（隔离→阻断→诱饵→监控），再按策略生成详细 DefenseAction 列表。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = IRPlannerResult
    TEMPERATURE = 0.3

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化响应规划 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``IRPlannerAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def plan_response(self, hypotheses: list[dict]) -> ResponsePlan:
        """根据威胁狩猎假设生成事件响应计划。

        将假设列表直接序列化为 JSON 交给 LLM，SDK 自动处理 JSON 解析与
        Pydantic 验证，最终将 :class:`IRPlannerResult` 转为 ``ResponsePlan``
        （protocol dataclass）返回。actions 转为 dict 列表以保持与原接口
        兼容（调用方按 dict 方式访问动作字段）。

        Args:
            hypotheses: 威胁狩猎假设列表，每条为包含 hypothesis/confidence/technique 的 dict。

        Returns:
            规划出的响应计划；LLM 失败时返回默认空计划。
        """
        result = self._run(f"Plan response for: {json.dumps(hypotheses)}")
        # Pydantic Model → protocol dataclass 转换；actions 转 dict 保持原接口
        return ResponsePlan(
            plan_id=result.plan_id,
            actions=[a.model_dump() for a in result.actions],
            confidence=result.confidence,
            rollback=result.rollback,
        )

    def plan_response_with_strategy(self, hypotheses: list[dict]) -> ResponsePlan:
        """Plan 范式规划响应计划（AP1.3）。

        两阶段推理：
            1. 规划阶段：LLM 分析威胁假设，生成多阶段响应策略（隔离→阻断→诱饵→监控）。
            2. 执行阶段：按策略生成详细 DefenseAction 列表 + 置信度 + 回滚方案。

        与 :meth:`plan_response` 的区别：先规划再执行，响应计划更系统化。
        规划阶段失败时降级到直接 :meth:`plan_response`。

        Args:
            hypotheses: 威胁狩猎假设列表。

        Returns:
            规划出的响应计划（``ResponsePlan``）。
        """
        prompt = f"Plan response for: {json.dumps(hypotheses)}"
        result = self._run_with_plan(prompt, domain="incident_response")
        return ResponsePlan(
            plan_id=result.plan_id,
            actions=[a.model_dump() for a in result.actions],
            confidence=result.confidence,
            rollback=result.rollback,
        )
