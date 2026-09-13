# date: 2026-07-06
# dev: myf
# changelog: AP4.3 接入 Ask 范式——继承 AskMode，新增 critique_with_human_check（严重度阈值请求人工复核 + 超时降级）
"""紫队对抗性批判 Agent 模块（SDK 结构化输出版 + Ask 范式）。

本模块实现紫队批判角色，对红队攻击链或蓝队响应方案进行自动化校验，
依据 ATT&CK 规则与防御完整性原则输出结构化评估结果，用于支撑
紫队闭环中的"对抗性校验"环节。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
AP4.3：``critique_with_human_check`` 在判定严重度达到阈值时暂停请求人工复核，
超时降级为确认批判结论并标记。
"""
from __future__ import annotations

import json

from agents import Agent, AgentOutputSchema

from aegisos_agents.action.output_types import CritiqueResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import (
    AskMode,
    AskResponse,
    AutoAskHandler,
    severity_at_least,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider

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


class CriticAgent(StructuredAgent[CritiqueResult], AskMode):
    """紫队对抗性批判 Agent（SDK 结构化输出 + Ask 范式）。

    通过调用 LLM 对红队攻击链或蓝队响应方案进行对抗性校验，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`CritiqueResult`
    （Pydantic 验证 + 自动重试），再转为 dict 返回。

    初始化时预建红/蓝两个 SDK Agent（分别使用对应阵营的系统提示词），
    ``critique`` 调用时按 ``side`` 参数切换使用哪个 Agent。
    AP4.3：``critique_with_human_check`` 在严重度达阈值时暂停请求人工复核。

    Attributes:
        SYSTEM_PROMPT: 默认系统提示词（红队），供基类构造首个 SDK Agent。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`CritiqueResult`。
        TEMPERATURE: 采样温度，0.3 保证评估输出稳定、可复现。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT_RED  # 默认红队，基类据此构造 self._sdk_agent
    OUTPUT_TYPE = CritiqueResult
    TEMPERATURE = 0.3

    def __init__(
        self,
        provider=None,
        mock: MockProvider | None = None,
        model=None,
        ask_handler=None,
    ) -> None:
        """初始化批判 Agent，预建红/蓝双 SDK Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``CriticAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
            model: SDK ``Model`` 实例（真实 API 模式）。
            ask_handler: 可选 :class:`AskHandler`（人机协同）；None 时退化为
                :class:`AutoAskHandler`（无人值守即时安全降级）。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        # 基类用 SYSTEM_PROMPT(=RED) 构造 self._sdk_agent；保存红队引用
        super().__init__(model=model, mock=mock)
        # AP4.3: 注入 Ask handler（无人值守时 AutoAskHandler 即时降级）
        self._ask_handler = ask_handler or AutoAskHandler()
        self._sdk_agent_red: Agent = self._sdk_agent
        # 另构造蓝队批判 SDK Agent，供 critique(side="blue") 切换使用
        self._sdk_agent_blue: Agent = Agent(
            name=self.__class__.__name__,
            instructions=SYSTEM_PROMPT_BLUE,
            output_type=AgentOutputSchema(self.OUTPUT_TYPE, strict_json_schema=False),
            model=self._model,
            # R19：走基类 _model_settings()，否则 AEGIS_DISABLE_THINKING 对本
            # Agent 无效——critic 是实测单次耗时最高的环节（开思考偶发 160s+）。
            model_settings=self._model_settings(),
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

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4.3 新增 critique_with_human_check——严重度达阈值时暂停请求人工复核，超时降级为确认结论
    def critique_with_human_check(
        self,
        target: dict,
        side: str = "red",
        severity_threshold: str = "high",
        ask_handler=None,
    ) -> dict:
        """带人工复核的批判（AP4 人机协同）。

        先按既有逻辑批判（返回含 ``severity`` 的 dict），若判定严重度
        达到 ``severity_threshold`` 则暂停向人类请求复核；超时/无人值守
        时降级为「确认批判结论」并标记，保证不阻塞紫队校验链。

        与 :meth:`critique` 的区别：在严重度达阈值时插入人工复核闸门；
        结果 dict 额外附带 ``_human_check`` 字段记录人机交互结论。

        Args:
            target: 待评估的目标对象（红队攻击链 / 蓝队响应方案）。
            side: 阵营选择，"red" 红队攻击链，"blue" 蓝队响应方案。
            severity_threshold: 触发人工复核的严重度阈值（如 ``"high"``）。
            ask_handler: 可选 :class:`AskHandler`；None 时使用实例注入的 handler。

        Returns:
            批判结果 dict（同 :meth:`critique`），含 ``_human_check`` 交互记录。
        """
        # 先批判（复用既有 LLM 调用路径）
        result = self.critique(target, side=side)
        severity = result.get("severity", "none")

        if not severity_at_least(severity, severity_threshold):
            # 未达阈值：无需人工复核，记录免确认
            result["_human_check"] = {
                "answered": True,
                "answer": "未触发阈值，无需人工复核",
                "timeout": False,
            }
            return result

        # 设置本次使用的 handler（优先参数，其次实例注入）
        if ask_handler is not None:
            self.set_ask_handler(ask_handler)

        response = self.ask_human(
            question=(
                f"批判判定严重度={severity}（≥阈值 {severity_threshold}），"
                f"是否人工复核/升级？"
            ),
            options=["确认结论", "人工升级", "忽略"],
            context={"side": side, "severity": severity, "issues": result.get("issues", [])},
            # 无人值守/超时：确认批判结论，但保留超时标记供后续复审
            on_timeout=lambda req: AskResponse(
                answered=False,
                answer="确认结论",
                timeout=True,
                rationale="无人值守超时，确认批判结论并标记复审",
            ),
        )

        answer = response.answer
        human_check = {
            "answered": response.answered,
            "answer": answer,
            "timeout": response.timeout,
        }
        if answer == "人工升级":
            human_check["escalated"] = True
        result["_human_check"] = human_check
        return result
