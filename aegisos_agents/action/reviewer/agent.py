# date: 2026-07-06
# dev: myf
# changelog: 迁移到 SDK 结构化输出——用 StructuredAgent + ReviewResult 替代 json.loads+try/except（~78 行→~56 行）
# date: 2026-07-04
# dev: myf
# changelog: 紫队一致性审查 Agent
from __future__ import annotations

import json

from aegisos_agents.action.output_types import ReviewResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider

"""紫队一致性审查 Agent 模块（SDK 结构化输出版）。

本模块实现紫队审查角色，对多份异构产出（攻击链、响应方案、取证报告等）
进行跨产出一致性校验，输出包含一致性判定、发现列表与总体评估的结构化
结果，用于支撑紫队闭环中的"跨角色一致性审查"环节。SDK 的 ``output_type``
结构化输出自动处理 JSON 解析与 Pydantic 验证，无需手写
``json.loads + try/except``。
"""

# 一致性审查系统提示词：校验多份产出之间是否相互一致
SYSTEM_PROMPT = (
    "You are a consistency reviewer. Given multiple artifacts (attack chain, "
    "response plan, forensic report), check if they are mutually consistent. "
    "Return JSON: consistent (bool), findings (array of str), "
    "overall_assessment (str)."
)


class ReviewerAgent(StructuredAgent[ReviewResult]):
    """紫队一致性审查 Agent（SDK 结构化输出）。

    通过调用 LLM 对多份异构产出进行跨产出一致性校验，SDK 的
    ``output_type`` 机制自动将返回 JSON 解析为 :class:`ReviewResult`
    （Pydantic 验证 + 自动重试），再转为 dict 返回，用于发现红队攻击链、
    蓝队响应方案与取证报告之间的逻辑矛盾或信息缺失。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`ReviewResult`。
        TEMPERATURE: 采样温度，0.2 保证审查输出稳定、可复现。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = ReviewResult
    TEMPERATURE = 0.2

    def __init__(self, provider=None, mock: MockProvider | None = None) -> None:
        """初始化审查 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``ReviewerAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(mock=mock)

    def review(self, artifacts: dict) -> dict:
        """对多份异构产出进行一致性审查。

        将待审查的多份产出（攻击链、响应方案、取证报告等）序列化为
        JSON 交由 LLM 进行跨产出一致性校验，SDK 自动处理 JSON 解析与
        Pydantic 验证，最终转为 dict 返回。

        Args:
            artifacts: 待审查的产出集合，键为产出类型，值为产出内容。

        Returns:
            dict: 审查结果，包含以下字段：
                - consistent (bool): 产出之间是否一致。
                - findings (list[str]): 发现的不一致问题列表。
                - overall_assessment (str): 总体评估结论文本。
        """
        # default=str 确保 artifacts 中非 JSON 可序列化对象（如枚举/自定义类）转为字符串
        result = self._run(f"Review consistency: {json.dumps(artifacts, default=str)}")
        # Pydantic Model → dict 转换，保持原 dict 返回类型
        return result.model_dump()
