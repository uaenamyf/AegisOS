# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 紫队一致性审查 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a consistency reviewer. Given multiple artifacts (attack chain, "
    "response plan, forensic report), check if they are mutually consistent. "
    "Return JSON: consistent (bool), findings (array of str), "
    "overall_assessment (str)."
)


class ReviewerAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def review(self, artifacts: dict) -> dict:
        resp = self._provider.complete(LLMRequest(
            prompt=f"Review consistency: {json.dumps(artifacts, default=str)}",
            model_id="reviewer",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        ))
        if not resp.ok:
            return {"consistent": False, "findings": ["LLM error"], "overall_assessment": "error"}
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            return {"consistent": False, "findings": ["parse error"], "overall_assessment": "error"}
