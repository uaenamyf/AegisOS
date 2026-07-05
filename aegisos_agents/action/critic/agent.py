# date: 2026-07-06
# dev: myf
# changelog: 迁移到 SDK 结构化输出——用 StructuredAgent + CritiqueResult 替代 json.loads+try/except；__init__ 预建红/蓝双 SDK Agent，critique 按 side 切换（~85 行→~72 行）
# date: 2026-07-04
# dev: myf
# changelog: 紫队对抗性批判 Agent
from __future__ import annotations

import json

from agents import Agent, AgentOutputSchema, ModelSettings

from aegisos_agents.action.output_types import CritiqueResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider

"""紫队对抗性批判 Agent 模块（SDK 结构化输出版）。

本模块实现紫队批判角色，对红队攻击链或蓝队响应方案进行自动化校验，
依据 ATT&CK 规则与防御完整性原则输出结构化评估结果，用于支撑
紫队闭环中的"对抗性校验"环节。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
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


class CriticAgent(StructuredAgent[CritiqueResult]):
    """紫队对抗性批判 Agent（SDK 结构化输出）。

    通过调用 LLM 对红队攻击链或蓝队响应方案进行对抗性校验，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`CritiqueResult`
    （Pydantic 验证 + 自动重试），再转为 dict 返回。

    初始化时预建红/蓝两个 SDK Agent（分别使用对应阵营的系统提示词），
    ``critique`` 调用时按 ``side`` 参数切换使用哪个 Agent。

    Attributes:
        SYSTEM_PROMPT: 默认系统提示词（红队），供基类构造首个 SDK Agent。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`CritiqueResult`。
        TEMPERATURE: 采样温度，0.3 保证评估输出稳定、可复现。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT_RED  # 默认红队，基类据此构造 self._sdk_agent
    OUTPUT_TYPE = CritiqueResult
    TEMPERATURE = 0.3

    def __init__(self, provider=None, mock: MockProvider | None = None) -> None:
        """初始化批判 Agent，预建红/蓝双 SDK Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``CriticAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        # 基类用 SYSTEM_PROMPT(=RED) 构造 self._sdk_agent；保存红队引用
        super().__init__(mock=mock)
        self._sdk_agent_red: Agent = self._sdk_agent
        # 另构造蓝队批判 SDK Agent，供 critique(side="blue") 切换使用
        self._sdk_agent_blue: Agent = Agent(
            name=self.__class__.__name__,
            instructions=SYSTEM_PROMPT_BLUE,
            output_type=AgentOutputSchema(self.OUTPUT_TYPE, strict_json_schema=False),
            model=self._model,
            model_settings=ModelSettings(temperature=self.TEMPERATURE),
        )

    def critique(self, target: dict, side: str = "red") -> dict:
        """对红队攻击链或蓝队响应方案进行对抗性批判。

        根据 ``side`` 参数选择对应阵营的 SDK Agent，将待评估目标序列化为
        JSON 交由 LLM 校验，SDK 自动处理 JSON 解析与 Pydantic 验证，
        最终转为 dict 返回。

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
        # 依据阵营选择对应的 SDK Agent
        self._sdk_agent = self._sdk_agent_red if side == "red" else self._sdk_agent_blue
        result = self._run(f"Critique: {json.dumps(target)}")
        # Pydantic Model → dict 转换，保持原 dict 返回类型
        return result.model_dump()
