# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队威胁狩猎 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Alert

SYSTEM_PROMPT = (
    "You are a threat hunting agent. Given prioritized alerts, generate "
    "hunting hypotheses. Return JSON with a 'hypotheses' array. Each "
    "hypothesis has: hypothesis (str), confidence (float 0-1), technique (ATT&CK id)."
)


class ThreatHuntAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def hunt(self, alerts: list[Alert]) -> list[dict]:
        alerts_desc = json.dumps(
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
                temperature=0.5,
            )
        )
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return data.get("hypotheses", [])
        except (json.JSONDecodeError, KeyError):
            return []
