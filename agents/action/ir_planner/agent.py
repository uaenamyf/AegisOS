# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 蓝队响应规划 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import ResponsePlan

"""蓝队响应规划 Agent 模块。

本模块接收威胁狩猎阶段产出的假设列表，利用大语言模型生成
事件响应计划（``ResponsePlan``），包含隔离/阻断/誘饵/监控等
响应动作、整体置信度和回滚方案。
"""

SYSTEM_PROMPT = (
    "You are an incident response planner. Given threat hypotheses, "
    "return JSON with plan_id, actions (array of {action_id, kind "
    "isolate|block|decoy|monitor, target, rationale}), confidence (float), "
    "rollback (dict with enabled and steps)."
)


class IRPlannerAgent:
    """蓝队响应规划 Agent。

    接收威胁狩猎假设列表，利用大语言模型生成结构化的事件响应计划，
    输出 ``ResponsePlan`` 对象（含计划 ID、动作列表、置信度、回滚方案）。
    """

    def __init__(self, provider: ModelProvider):
        """初始化响应规划 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def plan_response(self, hypotheses: list[dict]) -> ResponsePlan:
        """根据威胁狩猎假设生成事件响应计划。

        将假设列表直接序列化为 JSON 交给 LLM，模型返回包含 plan_id、
        actions、confidence、rollback 的 JSON，解析为 ``ResponsePlan`` 对象。
        若模型调用失败或 JSON 解析失败，返回空的默认 ``ResponsePlan``。

        Args:
            hypotheses: 威胁狩猎假设列表，每条为包含 hypothesis/confidence/technique 的 dict。

        Returns:
            规划出的响应计划；调用失败或解析异常时返回默认空计划。
        """
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Plan response for: {json.dumps(hypotheses)}",  # 假设列表直接序列化
                model_id="ir-planner",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,  # 较低温度保证响应计划的稳定性
            )
        )
        if not resp.ok:
            return ResponsePlan(plan_id="", confidence=0.0)  # 调用失败返回空计划
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            return ResponsePlan(
                plan_id=data.get("plan_id", ""),
                actions=data.get("actions", []),  # 默认动作为空列表
                confidence=data.get("confidence", 0.0),  # 默认置信度为 0.0
                rollback=data.get("rollback", {}),  # 默认回滚为空 dict
            )
        except (json.JSONDecodeError, KeyError):
            return ResponsePlan(plan_id="", confidence=0.0)  # 解析失败返回空计划
