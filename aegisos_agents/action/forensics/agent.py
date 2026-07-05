# date: 2026-07-04
# dev: myf
# changelog: 蓝队取证 Agent
from __future__ import annotations

import json

from aegisos_agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import ResponsePlan

"""蓝队取证 Agent 模块。

本模块接收响应计划，利用大语言模型进行数字化取证分析，
输出取证报告（包含报告 ID、根因、事件时间线、整改建议），
为事后分析与防御改进提供依据。
"""

SYSTEM_PROMPT = (
    "You are a digital forensics agent. Given a response plan, return JSON "
    "with report_id, root_cause (str), timeline (array of {ts, event}), "
    "recommendations (array of str)."
)


class ForensicsAgent:
    """蓝队取证 Agent。

    接收事件响应计划，利用大语言模型进行数字化取证分析，
    输出取证报告 dict（包含报告 ID、根因、时间线、建议）。
    """

    def __init__(self, provider: ModelProvider):
        """初始化取证 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def investigate(self, plan: ResponsePlan) -> dict:
        """根据响应计划进行数字化取证分析。

        将响应计划信息序列化为 JSON 交给 LLM，模型返回取证报告 JSON，
        直接解析为 dict 返回。若模型调用失败或 JSON 解析失败，
        返回默认的空取证报告。

        Args:
            plan: 事件响应计划。

        Returns:
            取证报告 dict，包含 report_id/root_cause/timeline/recommendations；
            调用失败或解析异常时返回默认空报告。
        """
        plan_desc = json.dumps(  # 序列化响应计划供模型理解
            {
                "plan_id": plan.plan_id,
                "actions": plan.actions,
                "confidence": plan.confidence,
            }
        )
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Investigate: {plan_desc}",
                model_id="forensics",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,  # 较低温度保证取证分析的准确性
            )
        )
        if not resp.ok:
            return {"report_id": "", "root_cause": "unknown", "timeline": [], "recommendations": []}  # 调用失败返回默认报告
        try:
            return json.loads(resp.text)  # 直接返回模型输出的 JSON dict
        except (json.JSONDecodeError, KeyError):
            return {"report_id": "", "root_cause": "unknown", "timeline": [], "recommendations": []}  # 解析失败返回默认报告
