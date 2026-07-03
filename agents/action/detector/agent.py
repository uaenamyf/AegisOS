# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 蓝队入侵检测 Agent
from __future__ import annotations

import json

from protocol.cyber import Alert
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are an intrusion detection agent. Given an event stream, "
    "return JSON with an 'alerts' array. Each alert has: alert_id, "
    "severity (low|medium|high|critical), src, dst, technique (ATT&CK id), raw (dict)."
)


class DetectorAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def detect(self, event_stream: list[dict]) -> list[Alert]:
        resp = self._provider.complete(LLMRequest(
            prompt=f"Detect anomalies in: {json.dumps(event_stream)}",
            model_id="detector",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                Alert(
                    alert_id=a.get("alert_id", ""),
                    severity=a.get("severity", "low"),
                    src=a.get("src", ""),
                    dst=a.get("dst", ""),
                    technique=a.get("technique", ""),
                    raw=a.get("raw", {}),
                )
                for a in data.get("alerts", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
