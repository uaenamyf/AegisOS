# date: 2026-07-06
# dev: myf
# changelog: 新建 MockSDKModel——将项目 MockProvider 适配为 SDK Model 接口，让 Runner.run 在测试中走预置响应
"""Mock SDK Model —— 将项目 MockProvider 适配为 openai-agents SDK 的 Model 接口。

SDK 的 ``Runner.run()`` 需要一个 ``Model`` 实例发起 LLM 调用。本模块将项目的
:class:`MockProvider`（预置 JSON 响应表）包装为 SDK ``Model``，使 SDK 的
``Agent`` + ``Runner`` + ``output_type`` 结构化输出链路在**无真实 API** 的测试
与评委演示场景下也能完整运行。

工作原理：
    1. SDK ``Runner`` 调用 ``Model.get_response()`` 获取模型响应
    2. 本类将 SDK 的 Responses 格式 input 转为项目的 ``LLMRequest``
    3. 委托 :class:`MockProvider` 返回预置 JSON 文本
    4. 包装为 SDK ``ModelResponse`` 返回，SDK 再用 ``output_type`` 解析为 Pydantic 对象

这样 11 个攻防 Agent 统一走 SDK ``Agent(output_type=...)`` 路径，无论 Mock 还是
真实 API，都由 SDK 的结构化输出机制处理，彻底删除 11 处 ``json.loads + try/except``。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from agents.items import ModelResponse, TResponseInputItem, TResponseStreamEvent
from agents.models.interface import Model, ModelTracing

# SDK Responses 消息项类型（构造合法的 ModelResponse.output 所需）
from openai.types.responses import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText

# 导入项目自己的 MockProvider（注意：aegisos_agents，非 SDK 的 agents）
from aegisos_agents.tools.llms.base import LLMRequest
from aegisos_agents.tools.llms.mock_provider import MockProvider


def _extract_prompt(input: str | list[TResponseInputItem]) -> str:
    """从 SDK Responses 格式的 input 中提取用户 prompt 文本。

    SDK input 可能是纯字符串，也可能是 Responses 消息项列表
    （含 ``{"role": "user", "content": "..."}`` 等结构）。

    Args:
        input: SDK ``Runner`` 传入的输入。

    Returns:
        提取出的用户 prompt 文本；无法提取时返回 JSON 序列化串兜底。
    """
    if isinstance(input, str):
        return input
    # Responses 格式：拼接所有 user 消息的 content
    parts: list[str] = []
    for item in input:
        content = item.get("content") if isinstance(item, dict) else None
        if content:
            parts.append(str(content))
    return " ".join(parts) if parts else json.dumps(input, default=str)


class MockSDKModel(Model):
    """SDK ``Model`` 接口的 Mock 实现 —— 包装项目 :class:`MockProvider`。

    让 SDK ``Runner.run()`` 在无真实 API 时走预置响应表，配合 ``output_type``
    实现结构化输出的 Mock 测试闭环。

    Attributes:
        _mock: 被包装的 :class:`MockProvider` 实例。
    """

    def __init__(self, mock: MockProvider | None = None) -> None:
        """初始化 Mock SDK Model。

        Args:
            mock: :class:`MockProvider` 实例；为 ``None`` 时新建空 Mock。
        """
        self._mock = mock or MockProvider()

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any | None,
    ) -> ModelResponse:
        """SDK ``Model`` 接口实现 —— 委托 MockProvider 返回预置响应。

        将 SDK 调用参数转为 ``LLMRequest``，经 MockProvider 取预置 JSON 文本，
        包装为 SDK ``ModelResponse`` 返回。SDK 随后用 ``output_type`` 解析。

        Args:
            system_instructions: 系统提示词。
            input: 用户输入（str 或 Responses 消息项列表）。
            其余参数由 SDK 传入，Mock 模式下不使用。

        Returns:
            :class:`ModelResponse`，含预置 JSON 文本作为输出。
        """
        prompt_text = _extract_prompt(input)
        llm_resp = self._mock.complete(
            LLMRequest(
                prompt=prompt_text,
                model_id="mock-sdk",
                system_prompt=system_instructions or "",
            )
        )
        # 构造合法的 SDK ModelResponse：output 为 ResponseOutputMessage
        # 含 id/content/role/status/type 字段（SDK 严格校验）
        import uuid

        text_output = ResponseOutputText(
            text=llm_resp.text,
            type="output_text",
            annotations=[],  # SDK 要求字段
        )
        message = ResponseOutputMessage(
            id=f"msg_{uuid.uuid4().hex[:24]}",
            content=[text_output],
            role="assistant",
            status="completed",
            type="message",
        )
        from agents.usage import Usage

        return ModelResponse(
            output=[message],
            usage=Usage(input_tokens=len(prompt_text) // 4, output_tokens=len(llm_resp.text) // 4),
            response_id=f"resp_{uuid.uuid4().hex[:24]}",
        )

    def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any | None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        """流式响应接口 —— Mock 模式不支持流式，抛 NotImplementedError。"""
        raise NotImplementedError("MockSDKModel 不支持流式响应；Mock 模式仅用同步调用")
