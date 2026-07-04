# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 蓝队告警分诊 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Alert

"""蓝队告警分诊 Agent 模块。

本模块接收入侵检测阶段产出的告警列表，利用大语言模型进行去重和
按严重级别排序，输出优先级排序后的告警列表，为后续威胁狩猎和
响应规划提供高优先级输入。
"""

# 告警严重级别排序权重：数值越小优先级越高
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SYSTEM_PROMPT = (
    "You are an alert triage agent. Given alerts, return JSON with an "
    "'alerts' array containing deduplicated, severity-ordered alerts. "
    "Each alert has alert_id and severity."
)


class TriageAgent:
    """蓝队告警分诊 Agent。

    接收原始告警列表，利用大语言模型进行去重和优先级排序，
    输出按严重级别排序后的告警列表。若模型调用失败，则退回
    原始告警列表作为 fallback。
    """

    def __init__(self, provider: ModelProvider):
        """初始化告警分诊 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def triage(self, alerts: list[Alert]) -> list[Alert]:
        """对告警列表进行去重和优先级排序。

        将告警信息序列化为 JSON 交给 LLM，模型返回去重排序后的
        alert_id 列表，据此从原始告警中映射出排序后的 ``Alert`` 对象。
        若模型调用失败，返回原始告警列表；若解析结果为空，也返回
        原始告警列表。

        Args:
            alerts: 待分诊的原始告警列表。

        Returns:
            分诊排序后的告警列表；异常时回退返回原始告警列表。
        """
        alerts_desc = json.dumps(  # 将告警信息序列化为 JSON 供模型理解
            [
                {"alert_id": a.alert_id, "severity": a.severity, "src": a.src, "dst": a.dst}
                for a in alerts
            ]
        )
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Triage these alerts: {alerts_desc}",
                model_id="triage",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.1,  # 极低温度保证排序结果的确定性
            )
        )
        if not resp.ok:
            return alerts  # fallback: 返回原始告警列表
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            ordered_ids = [a.get("alert_id", "") for a in data.get("alerts", [])]  # 模型排序后的 alert_id 序列
            alert_map = {a.alert_id: a for a in alerts}  # 构建 alert_id -> Alert 的映射
            result = [alert_map[aid] for aid in ordered_ids if aid in alert_map]  # 按模型顺序重建列表
            return result if result else alerts  # 结果为空时回退原始告警
        except (json.JSONDecodeError, KeyError):
            return alerts  # JSON 解析失败，回退原始告警
