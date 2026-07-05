# date: 2026-07-04
# dev: myf
# changelog: 蓝队入侵检测 Agent
from __future__ import annotations

import json

from aegisos_agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Alert

"""蓝队入侵检测 Agent 模块。

本模块接收事件流（以 dict 列表形式），利用大语言模型检测其中的
异常行为并生成告警（``Alert``），标注严重级别、源/目的资产及
关联的 ATT&CK 技术编号。
"""

SYSTEM_PROMPT = (
    "You are an intrusion detection agent. Given an event stream, "
    "return JSON with an 'alerts' array. Each alert has: alert_id, "
    "severity (low|medium|high|critical), src, dst, technique (ATT&CK id), raw (dict)."
)


class DetectorAgent:
    """蓝队入侵检测 Agent。

    接收事件流，利用大语言模型识别异常行为并生成结构化告警。
    输出 ``Alert`` 列表，每条告警包含严重级别、源/目的资产、
    ATT&CK 技术编号和原始数据。
    """

    def __init__(self, provider: ModelProvider):
        """初始化入侵检测 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def detect(self, event_stream: list[dict]) -> list[Alert]:
        """对事件流进行异常检测，生成告警列表。

        将事件流序列化为 JSON 交给 LLM，模型返回 alerts 数组，
        逐条解析为 ``Alert`` 对象。若模型调用失败或 JSON 解析
        失败，返回空列表。

        Args:
            event_stream: 原始事件流，每个元素为描述一条事件的 dict。

        Returns:
            检测出的告警列表；调用失败或解析异常时返回空列表。
        """
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Detect anomalies in: {json.dumps(event_stream)}",  # 事件流直接序列化
                model_id="detector",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,  # 低温度保证检测结果的稳定性
            )
        )
        if not resp.ok:
            return []  # 模型调用失败，返回空列表
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            return [
                Alert(
                    alert_id=a.get("alert_id", ""),
                    severity=a.get("severity", "low"),  # 默认严重级别为 low
                    src=a.get("src", ""),
                    dst=a.get("dst", ""),
                    technique=a.get("technique", ""),
                    raw=a.get("raw", {}),  # 原始数据默认为空 dict
                )
                for a in data.get("alerts", [])  # 遍历 alerts 数组
            ]
        except (json.JSONDecodeError, KeyError):
            return []  # JSON 解析失败或字段缺失，返回空列表
