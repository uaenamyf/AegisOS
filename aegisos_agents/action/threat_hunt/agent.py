# date: 2026-07-06
# dev: myf
# changelog: AP4.4 接入 Ask 范式——继承 AskMode，新增 hunt_with_human_check（不确定时暂停澄清 + 超时降级）
"""蓝队威胁狩猎 Agent 模块（SDK 结构化输出版 + Ask 范式）。

本模块接收优先排序后的告警列表，利用大语言模型生成威胁狩猎假设
（hypotheses），每条假设包含假说描述、置信度和关联的 ATT&CK 技术
编号，为后续响应规划提供决策依据。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
AP4.4：``hunt_with_human_check`` 在假设置信度偏低时暂停向人类澄清，
超时降级为保持当前假设。
"""
from __future__ import annotations

import json

from aegisos_agents.action.output_types import ThreatHuntResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import (
    AskMode,
    AskResponse,
    AutoAskHandler,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert

SYSTEM_PROMPT = (
    "You are a threat hunting agent. Given prioritized alerts, generate "
    "hunting hypotheses. Return JSON with a 'hypotheses' array. Each "
    "hypothesis has: hypothesis (str), confidence (float 0-1), technique (ATT&CK id)."
)


class ThreatHuntAgent(StructuredAgent[ThreatHuntResult], AskMode):
    """蓝队威胁狩猎 Agent（SDK 结构化输出 + Ask 范式）。

    接收优先级排序后的告警列表，利用大语言模型生成威胁狩猎假设，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`ThreatHuntResult`
    （Pydantic 验证 + 自动重试），再转为 dict 列表返回。
    AP4.4：``hunt_with_human_check`` 在不确定（低置信度）时暂停向人类澄清。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`ThreatHuntResult`。
        TEMPERATURE: 采样温度，0.5 鼓励假说多样性。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = ThreatHuntResult
    TEMPERATURE = 0.5

    def __init__(
        self,
        provider=None,
        mock: MockProvider | None = None,
        model=None,
        ask_handler=None,
    ) -> None:
        """初始化威胁狩猎 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``ThreatHuntAgent(provider=mock)``）无需改动。

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
        super().__init__(model=model, mock=mock)
        # AP4.4: 注入 Ask handler（无人值守时 AutoAskHandler 即时降级）
        self._ask_handler = ask_handler or AutoAskHandler()

    def hunt(self, alerts: list[Alert]) -> list[dict]:
        """根据告警列表生成威胁狩猎假设。

        将告警信息序列化为 JSON 交给 LLM，SDK 自动处理 JSON 解析与
        Pydantic 验证，最终将 :class:`HuntHypothesisModel` 转为 dict
        返回，保持接口兼容。

        Args:
            alerts: 优先排序后的告警列表。

        Returns:
            狩猎假设列表（每条为 dict）；LLM 失败时返回空列表。
        """
        alerts_desc = json.dumps(  # 将告警信息序列化为 JSON 供模型理解
            [
                {"alert_id": a.alert_id, "severity": a.severity, "technique": a.technique}
                for a in alerts
            ]
        )
        result = self._run(f"Generate hunting hypotheses for: {alerts_desc}")
        # Pydantic Model → dict 转换，保持原 list[dict] 返回类型
        return [h.model_dump() for h in result.hypotheses]

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4.4 新增 hunt_with_human_check——假设置信度偏低时暂停澄清，超时降级为保持当前假设
    def hunt_with_human_check(
        self,
        alerts: list[Alert],
        confidence_threshold: float = 0.5,
        ask_handler=None,
    ) -> list[dict]:
        """带人工澄清的威胁狩猎（AP4 人机协同）。

        先按既有逻辑生成狩猎假设，若存在置信度低于 ``confidence_threshold``
        的「不确定」假设，则暂停向人类澄清狩猎范围/约束；超时/无人值守
        时降级为「保持当前假设」，确保狩猎不阻塞后续响应规划。

        与 :meth:`hunt` 的区别：在低置信度假设出现时插入人工澄清闸门；
        人类选择「缩小范围重试」会重新提交收敛范围的 prompt 以精炼假设。

        Args:
            alerts: 优先排序后的告警列表。
            confidence_threshold: 触发澄清的置信度下限，低于此值视为不确定。
            ask_handler: 可选 :class:`AskHandler`；None 时使用实例注入的 handler。

        Returns:
            狩猎假设列表（list[dict]）；经人工澄清/降级后的版本。
        """
        # 先生成假设（复用既有 LLM 调用路径）
        hypotheses = self.hunt(alerts)

        uncertain = [
            h for h in hypotheses if (h.get("confidence") or 1.0) < confidence_threshold
        ]
        if not uncertain:
            # 全部假设置信度足够：无需澄清
            return hypotheses

        # 设置本次使用的 handler（优先参数，其次实例注入）
        if ask_handler is not None:
            self.set_ask_handler(ask_handler)

        response = self.ask_human(
            question=(
                f"部分假设置信度低于 {confidence_threshold}，"
                f"请确认狩猎范围/约束是否调整？"
            ),
            options=["保持当前假设", "缩小范围重试", "补充上下文"],
            context={
                "uncertain_hypotheses": [
                    h.get("hypothesis", "") for h in uncertain
                ],
                "confidence_threshold": confidence_threshold,
            },
            # 无人值守/超时：保持当前假设，不阻塞后续流程
            on_timeout=lambda req: AskResponse(
                answered=False,
                answer="保持当前假设",
                timeout=True,
                rationale="无人值守超时，保持当前假设",
            ),
        )

        answer = response.answer
        if answer == "缩小范围重试":
            # 收敛范围重跑：在 prompt 中追加收缩指令，由 LLM 精炼假设
            alerts_desc = json.dumps(
                [
                    {
                        "alert_id": a.alert_id,
                        "severity": a.severity,
                        "technique": a.technique,
                    }
                    for a in alerts
                ]
            )
            narrowed_prompt = (
                f"Generate hunting hypotheses for: {alerts_desc} "
                f"(NARROW SCOPE: focus only on high-confidence ATT&CK "
                f"techniques, reduce blast radius)"
            )
            narrowed = self._run(narrowed_prompt)
            return [h.model_dump() for h in narrowed.hypotheses]
        # 保持当前假设 / 超时默认 / 补充上下文（无法在循环内获取自由文本）：返回原假设
        return hypotheses
