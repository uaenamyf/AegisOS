# date: 2026-07-04
# dev: myf
# changelog: 多模型兼容层抽象接口
"""LLM 多模型兼容层的抽象接口定义。

本模块定义了与具体厂商无关的 LLM 请求/响应数据结构，
以及所有 Provider 必须实现的统一 Protocol 接口。

核心概念：
- LLMRequest：封装一次推理请求（prompt、模型、温度等）
- LLMResponse：封装一次推理结果（文本、成功标志、用量统计）
- ModelProvider：所有具体 Provider（OpenAI / Anthropic / Local / Mock）的统一接口
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMRequest:
    """一次 LLM 推理请求的不可变描述。

    封装发送给底层模型所需的全部参数，
    与具体厂商 API 无关，由各 Provider 自行翻译为对应格式。

    Attributes:
        prompt: 用户输入的提示文本。
        model_id: 目标模型标识符，如 ``"gpt-4o-mini"``、
            ``"claude-sonnet-4-20250514"``；为空字符串时由 Provider 使用自身默认模型。
        temperature: 采样温度，控制输出随机性，范围 0.0–2.0，默认 0.7。
        max_tokens: 生成 token 数量上限，默认 2048。
        system_prompt: 系统提示词，用于设定模型角色/约束；为空表示不发送 system 消息。
        stop: 停止序列列表；当输出匹配其中任一字符串时提前终止生成。
    """

    prompt: str
    model_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    # 使用 field(default_factory=list) 避免 list 作为默认值时的可变默认参数陷阱
    stop: list = field(default_factory=list)


@dataclass
class LLMResponse:
    """一次 LLM 推理结果的统一封装。

    无论底层 Provider 返回什么格式，都会被规范化为此结构，
    方便上层代码统一处理成功与失败两种情况。

    Attributes:
        text: 模型生成的文本内容；失败时为空字符串。
        ok: 请求是否成功完成；``True`` 表示正常返回，``False`` 表示出错。
        error: 失败时的错误描述；成功时为空字符串。
        usage: token 用量统计字典（如 ``{"prompt_tokens": ...,
            "completion_tokens": ...}``）；无用量信息时为空字典。
        model_id: 实际使用的模型标识符，便于日志追踪。
    """

    text: str = ""
    ok: bool = True
    error: str = ""
    usage: dict = field(default_factory=dict)
    model_id: str = ""


class ModelProvider(Protocol):
    """所有 LLM Provider 的统一接口协议。

    定义了 ``complete`` 方法签名，具体 Provider（OpenAIProvider、
    AnthropicProvider、LocalProvider、MockProvider 等）需实现该协议。
    使用 ``Protocol`` 而非抽象基类，便于鸭子类型，无需显式继承。
    """

    def complete(self, request: LLMRequest) -> LLMResponse:
        """执行一次 LLM 推理请求。

        Args:
            request: 包含 prompt、模型、温度等参数的请求对象。

        Returns:
            封装了生成文本（或错误信息）的 :class:`LLMResponse`。

        Raises:
            本接口本身不声明异常；具体实现应捕获所有异常并封装到
            ``LLMResponse.ok=False`` 中，避免向上层抛出。
        """
        ...
