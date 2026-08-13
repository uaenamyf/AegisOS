# date: 2026-07-06
# dev: myf
# change: 2026-08-12 overwhelmingly — AP2.4 接入 ReAct 告警关联工具循环
"""蓝队入侵检测 Agent 模块（SDK 结构化输出版）。

本模块接收事件流（以 dict 列表形式），利用大语言模型检测其中的
异常行为并生成告警（``Alert``），标注严重级别、源/目的资产及
关联的 ATT&CK 技术编号。使用 openai-agents SDK 的 ``output_type``
结构化输出，由 SDK 自动处理 JSON 解析与 Pydantic 验证，无需手写
``json.loads + try/except``。
"""

from __future__ import annotations

import json

from aegisos_agents.action.output_types import DetectorResult
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
    "You are an intrusion detection agent. Given an event stream, "
    "return JSON with an 'alerts' array. Each alert has: alert_id, "
    "severity (low|medium|high|critical), src, dst, technique (ATT&CK id), raw (dict)."
)


class DetectorAgent(StructuredAgent[DetectorResult]):
    """蓝队入侵检测 Agent（SDK 结构化输出）。

    接收事件流，利用大语言模型识别异常行为并生成结构化告警。
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`DetectorResult`
    （Pydantic 验证 + 自动重试），再转为 ``Alert`` 列表返回。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`DetectorResult`。
        TEMPERATURE: 采样温度，0.2 保证检测结果稳定。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = DetectorResult
    TEMPERATURE = 0.2

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化入侵检测 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``DetectorAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def detect(self, event_stream: list[dict]) -> list[Alert]:
        """对事件流进行异常检测，生成告警列表。

        SDK 自动处理 LLM 调用 → JSON 解析 → Pydantic 验证，失败时 SDK 内部
        自动重试。最终将 :class:`AlertModel` 转为 ``Alert``（protocol dataclass）
        返回，保持接口兼容。

        Args:
            event_stream: 原始事件流，每个元素为描述一条事件的 dict。

        Returns:
            检测出的告警列表；LLM 失败时返回空列表。
        """
        result = self._run(f"Detect anomalies in: {json.dumps(event_stream)}")
        # Pydantic Model → protocol dataclass 转换
        return [
            Alert(
                alert_id=a.alert_id,
                severity=a.severity,
                src=a.src,
                dst=a.dst,
                technique=a.technique,
                raw=a.raw,
            )
            for a in result.alerts
        ]

    def detect_react(
        self,
        event_stream: list[dict[str, object]],
        executor: ReactExecutor,
        *,
        thinker: ReactThinker[list[Alert]] | None = None,
        max_iterations: int = 8,
        stop_on_tool_error: bool = True,
    ) -> ReactResult[list[Alert]]:
        """通过 ReAct 关联事件观察，再生成检测告警。

        Args:
            event_stream: 需要关联分析的原始事件流。
            executor: 执行 ``correlate_alerts`` 的受控工具端口。
            thinker: 可选自定义思考器，用于多工具策略。
            max_iterations: 最大 ReAct 循环轮数。
            stop_on_tool_error: 是否在工具失败时立即停止。

        Returns:
            带完整轨迹的检测告警结果。
        """

        def finalize(observation: ToolResult) -> list[Alert]:
            result = self._run(
                f"Detect anomalies in {json.dumps(event_stream)} using correlation observation: "
                f"{render_tool_output(observation.output)}"
            )
            return [
                Alert(
                    alert_id=alert.alert_id,
                    severity=alert.severity,
                    src=alert.src,
                    dst=alert.dst,
                    technique=alert.technique,
                    raw=alert.raw,
                )
                for alert in result.alerts
            ]

        return run_tool_react(
            goal=f"Detect threats in {len(event_stream)} events",
            action=ToolCall(
                name="correlate_alerts",
                args={"alerts": event_stream},
                permission="telemetry.read",
            ),
            executor=executor,
            finalizer=finalize,
            action_thought="需要先关联原始遥测事件以识别攻击模式",
            finish_thought="事件关联观察已经足够生成检测告警",
            thinker=thinker,
            max_iterations=max_iterations,
            stop_on_tool_error=stop_on_tool_error,
        )
