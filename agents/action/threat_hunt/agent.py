# date: 2026-07-04
# dev: myf
# changelog: 蓝队威胁狩猎 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Alert

"""蓝队威胁狩猎 Agent 模块。

本模块接收优先排序后的告警列表，利用大语言模型生成威胁狩猎假设
（hypotheses），每条假设包含假说描述、置信度和关联的 ATT&CK 技术
编号，为后续响应规划提供决策依据。
"""

SYSTEM_PROMPT = (
    "You are a threat hunting agent. Given prioritized alerts, generate "
    "hunting hypotheses. Return JSON with a 'hypotheses' array. Each "
    "hypothesis has: hypothesis (str), confidence (float 0-1), technique (ATT&CK id)."
)


class ThreatHuntAgent:
    """蓝队威胁狩猎 Agent。

    接收优先级排序后的告警列表，利用大语言模型生成威胁狩猎假设，
    输出假设列表（每条包含假说描述、置信度、ATT&CK 技术编号）。
    """

    def __init__(self, provider: ModelProvider):
        """初始化威胁狩猎 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def hunt(self, alerts: list[Alert]) -> list[dict]:
        """根据告警列表生成威胁狩猎假设。

        将告警信息序列化为 JSON 交给 LLM，模型返回 hypotheses 数组，
        直接返回该数组（每条为包含 hypothesis/confidence/technique 的 dict）。
        若模型调用失败或 JSON 解析失败，返回空列表。

        Args:
            alerts: 优先排序后的告警列表。

        Returns:
            狩猎假设列表；调用失败或解析异常时返回空列表。
        """
        alerts_desc = json.dumps(  # 将告警信息序列化为 JSON 供模型理解
            [
                {"alert_id": a.alert_id, "severity": a.severity, "technique": a.technique}
                for a in alerts
            ]
        )
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Generate hunting hypotheses for: {alerts_desc}",
                model_id="threat-hunt",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.5,  # 中高温度鼓励假说多样性
            )
        )
        if not resp.ok:
            return []  # 模型调用失败，返回空列表
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            return data.get("hypotheses", [])  # 直接返回 hypotheses 数组
        except (json.JSONDecodeError, KeyError):
            return []  # JSON 解析失败或字段缺失，返回空列表
