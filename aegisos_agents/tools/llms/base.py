# date: 2026-07-04
# dev: myf
# changelog: R5.1 清理——删除 ModelProvider Protocol（SDK 有自己的 ModelProvider），保留 LLMRequest/LLMResponse（MockProvider 内部契约）
"""LLM 请求/响应数据结构（Mock 内部契约）。

R5.1 清理后：
    - 删除 ``ModelProvider`` Protocol（SDK 已有自己的 ``ModelProvider``，
      真实 API 走 ``SDKProvider.get_sdk_model()`` 注入 SDK ``Model``）。
    - 保留 ``LLMRequest`` / ``LLMResponse`` 作为 :class:`MockProvider` 与
      :class:`MockSDKModel` 之间的内部数据契约（Mock 模式基础设施，
      测试依赖）。

历史：
    - 原 ``ModelProvider`` Protocol 被 SDK ``ModelProvider`` + ``SDKProvider`` 替代
    - 11 个攻防 Agent 已迁移到 ``StructuredAgent``（SDK ``Agent(output_type=...)``）
    - ``neuro_symbolic`` 已迁移到 ``NeuroSymbolicAgent``（SDK 结构化输出）
    - ``model_router`` 已删除（R5.2）
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    """一次 LLM 推理请求的描述（Mock 内部契约）。

    封装发送给底层模型所需的全部参数。Mock 模式下由 :class:`MockSDKModel`
    从 SDK ``Runner`` 转换而来，传给 :class:`MockProvider`。

    Attributes:
        prompt: 用户输入的提示文本。
        model_id: 目标模型标识符；为空字符串时由 Provider 使用自身默认模型。
        temperature: 采样温度，控制输出随机性，范围 0.0–2.0，默认 0.7。
        max_tokens: 生成 token 数量上限，默认 2048。
        system_prompt: 系统提示词；为空表示不发送 system 消息。
        stop: 停止序列列表；当输出匹配其中任一字符串时提前终止生成。
    """

    prompt: str
    model_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    stop: list = field(default_factory=list)


@dataclass
class LLMResponse:
    """一次 LLM 推理结果的封装（Mock 内部契约）。

    Attributes:
        text: 模型生成的文本内容；失败时为空字符串。
        ok: 请求是否成功完成；``True`` 表示正常返回，``False`` 表示出错。
        error: 失败时的错误描述；成功时为空字符串。
        usage: token 用量统计字典；无用量信息时为空字典。
        model_id: 实际使用的模型标识符，便于日志追踪。
    """

    text: str = ""
    ok: bool = True
    error: str = ""
    usage: dict = field(default_factory=dict)
    model_id: str = ""
