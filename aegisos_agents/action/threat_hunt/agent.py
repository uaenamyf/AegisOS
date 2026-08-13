# date: 2026-07-06
# dev: myf
# change: 2026-08-12 overwhelmingly — AP2.5 接入 ReAct ATT&CK 查询工具循环
"""蓝队威胁狩猎 Agent 模块（SDK 结构化输出版）。

本模块接收优先排序后的告警列表，利用大语言模型生成威胁狩猎假设
（hypotheses），每条假设包含假说描述、置信度和关联的 ATT&CK 技术
编号，为后续响应规划提供决策依据。SDK 的 ``output_type`` 结构化输出
自动处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""

from __future__ import annotations

import json
from typing import cast

from aegisos_agents.action.output_types import ThreatHuntResult
from aegisos_agents.action.react_support import render_tool_output, run_tool_react
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import (
    ReactExecutor,
    ReactResult,
    ReactThinker,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert
from protocol.tool import ToolCall, ToolResult

SYSTEM_PROMPT = (
    "You are a threat hunting agent. Given prioritized alerts, generate "
    "hunting hypotheses. Return JSON with a 'hypotheses' array. Each "
    "hypothesis has: hypothesis (str), confidence (float 0-1), technique (ATT&CK id)."
)


class ThreatHuntAgent(StructuredAgent[ThreatHuntResult]):
    """蓝队威胁狩猎 Agent（SDK 结构化输出）。

    接收优先级排序后的告警列表，利用大语言模型生成威胁狩猎假设，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`ThreatHuntResult`
    （Pydantic 验证 + 自动重试），再转为 dict 列表返回。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`ThreatHuntResult`。
        TEMPERATURE: 采样温度，0.5 鼓励假说多样性。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = ThreatHuntResult
    TEMPERATURE = 0.5

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化威胁狩猎 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``ThreatHuntAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

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

    def hunt_react(
        self,
        alerts: list[Alert],
        executor: ReactExecutor,
        *,
        thinker: ReactThinker[list[dict[str, object]]] | None = None,
        max_iterations: int = 8,
        stop_on_tool_error: bool = True,
    ) -> ReactResult[list[dict[str, object]]]:
        """通过 ReAct 查询 ATT&CK 知识，再生成威胁狩猎假设。

        Args:
            alerts: 需要深入狩猎的优先告警。
            executor: 执行 ``query_attck_kb`` 的受控工具端口。
            thinker: 可选自定义思考器，用于多工具策略。
            max_iterations: 最大 ReAct 循环轮数。
            stop_on_tool_error: 是否在工具失败时立即停止。

        Returns:
            带完整轨迹的威胁狩猎假设。
        """
        alert_payload = [
            {
                "alert_id": alert.alert_id,
                "severity": alert.severity,
                "src": alert.src,
                "dst": alert.dst,
                "technique": alert.technique,
            }
            for alert in alerts
        ]
        technique_ids = list(dict.fromkeys(alert.technique for alert in alerts if alert.technique))

        def finalize(observation: ToolResult) -> list[dict[str, object]]:
            result = self._run(
                "Generate hunting hypotheses for alerts "
                f"{json.dumps(alert_payload)} using ATT&CK observation: "
                f"{render_tool_output(observation.output)}"
            )
            return [
                cast(dict[str, object], hypothesis.model_dump()) for hypothesis in result.hypotheses
            ]

        return run_tool_react(
            goal=f"Hunt threats from {len(alerts)} prioritized alerts",
            action=ToolCall(
                name="query_attck_kb",
                args={"technique_id": technique_ids[0] if technique_ids else ""},
                permission="knowledge.read",
            ),
            executor=executor,
            finalizer=finalize,
            action_thought="需要查询 ATT&CK 知识验证告警对应的攻击技战术",
            finish_thought="ATT&CK 查询观察已经足够生成狩猎假设",
            thinker=thinker,
            max_iterations=max_iterations,
            stop_on_tool_error=stop_on_tool_error,
        )
