# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 紫队对抗性批判 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT_RED = (
    "You are a red team critic. Given an attack chain, validate it against "
    "ATT&CK rules. Return JSON: valid (bool), issues (array), severity "
    "(none|low|medium|high), suggestion (str)."
)
SYSTEM_PROMPT_BLUE = (
    "You are a blue team critic. Given a response plan, validate it for "
    "completeness and correctness. Return JSON: valid (bool), issues (array), "
    "severity (none|low|medium|high), suggestion (str)."
)


class CriticAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def critique(self, target: dict, side: str = "red") -> dict:
        sys_prompt = SYSTEM_PROMPT_RED if side == "red" else SYSTEM_PROMPT_BLUE
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Critique: {json.dumps(target)}",
                model_id="critic",
                system_prompt=sys_prompt,
                temperature=0.3,
            )
        )
        if not resp.ok:
            return {"valid": False, "issues": ["LLM error"], "severity": "high", "suggestion": ""}
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, KeyError):
            return {"valid": False, "issues": ["parse error"], "severity": "high", "suggestion": ""}
