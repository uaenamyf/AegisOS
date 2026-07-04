# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 紫队一致性审查 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider

"""紫队一致性审查 Agent 模块。

本模块实现紫队审查角色，对多份异构产出（攻击链、响应方案、取证报告等）
进行跨产出一致性校验，输出包含一致性判定、发现列表与总体评估的结构化
JSON 结果，用于支撑紫队闭环中的"跨角色一致性审查"环节。
"""

# 一致性审查系统提示词：校验多份产出之间是否相互一致
SYSTEM_PROMPT = (
    "You are a consistency reviewer. Given multiple artifacts (attack chain, "
    "response plan, forensic report), check if they are mutually consistent. "
    "Return JSON: consistent (bool), findings (array of str), "
    "overall_assessment (str)."
)


class ReviewerAgent:
    """紫队一致性审查 Agent。

    通过调用 LLM 对多份异构产出进行跨产出一致性校验，输出包含一致性
    判定、发现列表与总体评估的结构化结果，用于发现红队攻击链、蓝队
    响应方案与取证报告之间的逻辑矛盾或信息缺失。

    Attributes:
        _provider: 底层模型提供者，用于发送 LLM 请求。
    """

    def __init__(self, provider: ModelProvider):
        """初始化审查 Agent。

        Args:
            provider: 模型提供者实例，封装具体 LLM 后端调用能力。
        """
        self._provider = provider

    def review(self, artifacts: dict) -> dict:
        """对多份异构产出进行一致性审查。

        将待审查的多份产出（攻击链、响应方案、取证报告等）序列化为
        JSON 交由 LLM 进行跨产出一致性校验，并解析返回结果。当 LLM
        调用失败或返回 JSON 解析失败时，回退为标记不一致的降级结果。

        Args:
            artifacts: 待审查的产出集合，键为产出类型，值为产出内容。

        Returns:
            dict: 审查结果，包含以下字段：
                - consistent (bool): 产出之间是否一致。
                - findings (list[str]): 发现的不一致问题列表。
                - overall_assessment (str): 总体评估结论文本。
        """
        resp = self._provider.complete(
            LLMRequest(
                # default=str 确保 artifacts 中非 JSON 可序列化对象（如枚举/自定义类）转为字符串
                prompt=f"Review consistency: {json.dumps(artifacts, default=str)}",
                model_id="reviewer",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,  # 极低温度保证审查输出稳定、可复现
            )
        )
        # LLM 调用失败时返回标记不一致的降级结果
        if not resp.ok:
            return {"consistent": False, "findings": ["LLM error"], "overall_assessment": "error"}
        try:
            # 尝试解析 LLM 返回的 JSON 文本为结构化审查结果
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            # 解析失败时回退为标记不一致的降级结果
            return {"consistent": False, "findings": ["parse error"], "overall_assessment": "error"}
