# date: 2026-07-06
# dev: myf
# changelog: 迁移到 SDK 结构化输出——用 StructuredAgent + ForensicsResult 替代 json.loads+try/except（~74 行→~54 行）
# date: 2026-07-04
# dev: myf
# changelog: 蓝队取证 Agent
from __future__ import annotations

import json

from aegisos_agents.action.output_types import ForensicsResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import ResponsePlan

"""蓝队取证 Agent 模块（SDK 结构化输出版）。

本模块接收响应计划，利用大语言模型进行数字化取证分析，
输出取证报告（包含报告 ID、根因、事件时间线、整改建议），
为事后分析与防御改进提供依据。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""

SYSTEM_PROMPT = (
    "You are a digital forensics agent. Given a response plan, return JSON "
    "with report_id, root_cause (str), timeline (array of {ts, event}), "
    "recommendations (array of str)."
)


class ForensicsAgent(StructuredAgent[ForensicsResult]):
    """蓝队取证 Agent（SDK 结构化输出）。

    接收事件响应计划，利用大语言模型进行数字化取证分析，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`ForensicsResult`
    （Pydantic 验证 + 自动重试），再转为 dict 返回。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`ForensicsResult`。
        TEMPERATURE: 采样温度，0.3 保证取证分析的准确性。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = ForensicsResult
    TEMPERATURE = 0.3

    def __init__(self, provider=None, mock: MockProvider | None = None) -> None:
        """初始化取证 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``ForensicsAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(mock=mock)

    def investigate(self, plan: ResponsePlan) -> dict:
        """根据响应计划进行数字化取证分析。

        将响应计划信息序列化为 JSON 交给 LLM，SDK 自动处理 JSON 解析与
        Pydantic 验证，最终将 :class:`ForensicsResult` 转为 dict 返回，
        保持接口兼容。

        Args:
            plan: 事件响应计划。

        Returns:
            取证报告 dict，包含 report_id/root_cause/timeline/recommendations；
            LLM 失败时由 SDK 重试机制处理。
        """
        plan_desc = json.dumps(  # 序列化响应计划供模型理解
            {
                "plan_id": plan.plan_id,
                "actions": plan.actions,
                "confidence": plan.confidence,
            }
        )
        result = self._run(f"Investigate: {plan_desc}")
        # Pydantic Model → dict 转换，保持原 dict 返回类型
        return result.model_dump()
