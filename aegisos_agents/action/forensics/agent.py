# date: 2026-07-06
# dev: myf
# change: 2026-08-12 overwhelmingly — AP2.6 接入 ReAct 取证证据工具循环
"""蓝队取证 Agent 模块（SDK 结构化输出版）。

本模块接收响应计划，利用大语言模型进行数字化取证分析，
输出取证报告（包含报告 ID、根因、事件时间线、整改建议），
为事后分析与防御改进提供依据。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import cast

from aegisos_agents.action.output_types import ForensicsResult
from aegisos_agents.action.react_support import render_tool_output, run_tool_react
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import (
    ReactExecutor,
    ReactResult,
    ReactThinker,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import DefenseAction, ResponsePlan
from protocol.tool import ToolCall, ToolResult

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

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
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
        super().__init__(model=model, mock=mock)

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
        plan_desc = json.dumps(self._plan_payload(plan))
        result = self._run(f"Investigate: {plan_desc}")
        # Pydantic Model → dict 转换，保持原 dict 返回类型
        return result.model_dump()

    def investigate_react(
        self,
        plan: ResponsePlan,
        executor: ReactExecutor,
        *,
        thinker: ReactThinker[dict[str, object]] | None = None,
        max_iterations: int = 8,
        stop_on_tool_error: bool = True,
    ) -> ReactResult[dict[str, object]]:
        """通过 ReAct 收集证据，再生成数字取证报告。

        Args:
            plan: 需要进行事后取证的响应计划。
            executor: 执行 ``collect_forensic_evidence`` 的受控工具端口。
            thinker: 可选自定义思考器，用于多工具策略。
            max_iterations: 最大 ReAct 循环轮数。
            stop_on_tool_error: 是否在工具失败时立即停止。

        Returns:
            带完整轨迹的取证报告。
        """
        plan_payload = self._plan_payload(plan)

        def finalize(observation: ToolResult) -> dict[str, object]:
            result = self._run(
                f"Investigate response plan {json.dumps(plan_payload)} using evidence: "
                f"{render_tool_output(observation.output)}"
            )
            return cast(dict[str, object], result.model_dump())

        return run_tool_react(
            goal=f"Investigate response plan {plan.plan_id}",
            action=ToolCall(
                name="collect_forensic_evidence",
                args={"plan": plan_payload},
                permission="evidence.read",
            ),
            executor=executor,
            finalizer=finalize,
            action_thought="需要先收集响应计划相关的取证证据",
            finish_thought="证据观察已经足够形成取证报告",
            thinker=thinker,
            max_iterations=max_iterations,
            stop_on_tool_error=stop_on_tool_error,
        )

    @staticmethod
    def _plan_payload(plan: ResponsePlan) -> dict[str, object]:
        """把 ResponsePlan 转换为可供工具和模型使用的 JSON 载荷。"""
        return {
            "plan_id": plan.plan_id,
            "actions": [
                asdict(action) if isinstance(action, DefenseAction) else action
                for action in plan.actions
            ],
            "confidence": plan.confidence,
            "rollback": plan.rollback,
        }
