# date: 2026-07-04
# dev: myf
# changelog: 紫队对抗性批判 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider

"""紫队对抗性批判 Agent 模块。

本模块实现紫队批判角色，对红队攻击链或蓝队响应方案进行自动化校验，
依据 ATT&CK 规则与防御完整性原则输出结构化 JSON 评估结果，用于支撑
紫队闭环中的"对抗性校验"环节。
"""

# 红队批判系统提示词：校验攻击链是否符合 ATT&CK 规则
SYSTEM_PROMPT_RED = (
    "You are a red team critic. Given an attack chain, validate it against "
    "ATT&CK rules. Return JSON: valid (bool), issues (array), severity "
    "(none|low|medium|high), suggestion (str)."
)
# 蓝队批判系统提示词：校验响应方案的完整性与正确性
SYSTEM_PROMPT_BLUE = (
    "You are a blue team critic. Given a response plan, validate it for "
    "completeness and correctness. Return JSON: valid (bool), issues (array), "
    "severity (none|low|medium|high), suggestion (str)."
)


class CriticAgent:
    """紫队对抗性批判 Agent。

    通过调用 LLM 对红队攻击链或蓝队响应方案进行对抗性校验，
    输出包含有效性判定、问题列表、严重度与改进建议的结构化评估结果。

    Attributes:
        _provider: 底层模型提供者，用于发送 LLM 请求。
    """

    def __init__(self, provider: ModelProvider):
        """初始化批判 Agent。

        Args:
            provider: 模型提供者实例，封装具体 LLM 后端调用能力。
        """
        self._provider = provider

    def critique(self, target: dict, side: str = "red") -> dict:
        """对红队攻击链或蓝队响应方案进行对抗性批判。

        根据 side 参数选择对应阵营的系统提示词，将待评估目标序列化为
        JSON 交由 LLM 校验，并解析返回结果。当 LLM 调用失败或返回
        JSON 解析失败时，回退为标记无效的高严重度结果。

        Args:
            target: 待评估的目标对象，红队场景为攻击链，蓝队场景为响应方案。
            side: 阵营选择，"red" 表示红队攻击链校验，其余值视为蓝队响应方案校验。

        Returns:
            dict: 批判结果，包含以下字段：
                - valid (bool): 目标是否通过校验。
                - issues (list[str]): 发现的问题列表。
                - severity (str): 严重度等级（none/low/medium/high）。
                - suggestion (str): 改进建议文本。
        """
        # 依据阵营选择对应的系统提示词
        sys_prompt = SYSTEM_PROMPT_RED if side == "red" else SYSTEM_PROMPT_BLUE
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Critique: {json.dumps(target)}",
                model_id="critic",
                system_prompt=sys_prompt,
                temperature=0.3,  # 低温度保证评估输出稳定、可复现
            )
        )
        # LLM 调用失败时返回标记无效的高严重度降级结果
        if not resp.ok:
            return {"valid": False, "issues": ["LLM error"], "severity": "high", "suggestion": ""}
        try:
            # 尝试解析 LLM 返回的 JSON 文本为结构化评估结果
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            # 解析失败时回退为标记无效的高严重度降级结果
            return {"valid": False, "issues": ["parse error"], "severity": "high", "suggestion": ""}
