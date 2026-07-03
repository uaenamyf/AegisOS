# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队取证 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import ResponsePlan

SYSTEM_PROMPT = (
    "You are a digital forensics agent. Given a response plan, return JSON "
    "with report_id, root_cause (str), timeline (array of {ts, event}), "
    "recommendations (array of str)."
)


class ForensicsAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def investigate(self, plan: ResponsePlan) -> dict:
        plan_desc = json.dumps(
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
                temperature=0.3,
            )
        )
        if not resp.ok:
            return {"report_id": "", "root_cause": "unknown", "timeline": [], "recommendations": []}
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            return {"report_id": "", "root_cause": "unknown", "timeline": [], "recommendations": []}
