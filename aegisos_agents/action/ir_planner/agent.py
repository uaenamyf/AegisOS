# date: 2026-07-06
# dev: myf
"""蓝队响应规划 Agent 模块（SDK 结构化输出版）。

本模块接收威胁狩猎阶段产出的假设列表，利用大语言模型生成
事件响应计划（``ResponsePlan``），包含隔离/阻断/誘饵/监控等
响应动作、整体置信度和回滚方案。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""
from __future__ import annotations

import json

from aegisos_agents.action.output_types import IRPlannerResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import ResponsePlan

SYSTEM_PROMPT = (
    "You are an incident response planner. Given threat hypotheses, "
    "return JSON with plan_id, actions (array of {action_id, kind "
    "isolate|block|decoy|monitor, target, rationale}), confidence (float), "
    "rollback (dict with enabled and steps)."
)


class IRPlannerAgent(StructuredAgent[IRPlannerResult]):
    """蓝队响应规划 Agent（SDK 结构化输出）。

    接收威胁狩猎假设列表，利用大语言模型生成结构化的事件响应计划，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`IRPlannerResult`
    （Pydantic 验证 + 自动重试），再转为 ``ResponsePlan`` 对象返回。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`IRPlannerResult`。
        TEMPERATURE: 采样温度，0.3 保证响应计划的稳定性。
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
