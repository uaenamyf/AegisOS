# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队告警分诊 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Alert

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SYSTEM_PROMPT = (
    "You are an alert triage agent. Given alerts, return JSON with an "
    "'alerts' array containing deduplicated, severity-ordered alerts. "
    "Each alert has alert_id and severity."
)


class TriageAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def triage(self, alerts: list[Alert]) -> list[Alert]:
        alerts_desc = json.dumps(
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
                temperature=0.1,
            )
        )
        if not resp.ok:
            return alerts  # fallback: return original
        try:
            data = json.loads(resp.text)
            ordered_ids = [a.get("alert_id", "") for a in data.get("alerts", [])]
            alert_map = {a.alert_id: a for a in alerts}
            result = [alert_map[aid] for aid in ordered_ids if aid in alert_map]
            return result if result else alerts
        except (json.JSONDecodeError, KeyError):
            return alerts
