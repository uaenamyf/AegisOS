# date: 2026-07-06
# dev: myf
"""蓝队告警分诊 Agent 模块（SDK 结构化输出版）。

本模块接收入侵检测阶段产出的告警列表，利用大语言模型进行去重和
按严重级别排序，输出优先级排序后的告警列表，为后续威胁狩猎和
响应规划提供高优先级输入。SDK 的 ``output_type`` 结构化输出自动
处理 JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""
from __future__ import annotations

import json

from aegisos_agents.action.output_types import TriageResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Alert

# 告警严重级别排序权重：数值越小优先级越高
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SYSTEM_PROMPT = (
    "You are an alert triage agent. Given alerts, return JSON with an "
    "'alerts' array containing deduplicated, severity-ordered alerts. "
    "Each alert has alert_id and severity."
)


class TriageAgent(StructuredAgent[TriageResult]):
    """蓝队告警分诊 Agent（SDK 结构化输出）。

    接收原始告警列表，利用大语言模型进行去重和优先级排序，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为 :class:`TriageResult`
    （Pydantic 验证 + 自动重试）。再据排序后的 alert_id 从原始告警中
    映射回 ``Alert`` 对象返回；结果为空时回退原始告警列表。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`TriageResult`。
        TEMPERATURE: 采样温度，0.1 保证排序结果的确定性。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = TriageResult
    TEMPERATURE = 0.1

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化告警分诊 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``TriageAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def triage(self, alerts: list[Alert]) -> list[Alert]:
        """对告警列表进行去重和优先级排序。

        将告警信息序列化为 JSON 交给 LLM，SDK 自动处理 JSON 解析与
        Pydantic 验证。模型返回排序后的 alert_id 序列，据此从原始
        告警中映射出排序后的 ``Alert`` 对象。结果为空时回退原始告警列表。

        Args:
            alerts: 待分诊的原始告警列表。

        Returns:
            分诊排序后的告警列表；结果为空时回退返回原始告警列表。
        """
        alerts_desc = json.dumps(  # 将告警信息序列化为 JSON 供模型理解
            [
                {"alert_id": a.alert_id, "severity": a.severity, "src": a.src, "dst": a.dst}
                for a in alerts
            ]
        )
        result = self._run(f"Triage these alerts: {alerts_desc}")
        # 模型排序后的 alert_id 序列
        ordered_ids = [a.alert_id for a in result.alerts]
        alert_map = {a.alert_id: a for a in alerts}  # 构建 alert_id -> Alert 的映射
        mapped = [alert_map[aid] for aid in ordered_ids if aid in alert_map]  # 按模型顺序重建列表
        return mapped if mapped else alerts  # 结果为空时回退原始告警
