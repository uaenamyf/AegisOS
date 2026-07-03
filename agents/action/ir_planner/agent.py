# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队响应规划 Agent
from __future__ import annotations

import json

from protocol.cyber import ResponsePlan
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are an incident response planner. Given threat hypotheses, "
    "return JSON with plan_id, actions (array of {action_id, kind "
    "isolate|block|decoy|monitor, target, rationale}), confidence (float), "
    "rollback (dict with enabled and steps)."
)


class IRPlannerAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def plan_response(self, hypotheses: list[dict]) -> ResponsePlan:
        resp = self._provider.complete(LLMRequest(
            prompt=f"Plan response for: {json.dumps(hypotheses)}",
            model_id="ir-planner",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        ))
        if not resp.ok:
            return ResponsePlan(plan_id="", confidence=0.0)
        try:
            data = json.loads(resp.text)
            return ResponsePlan(
                plan_id=data.get("plan_id", ""),
                actions=data.get("actions", []),
                confidence=data.get("confidence", 0.0),
                rollback=data.get("rollback", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return ResponsePlan(plan_id="", confidence=0.0)
