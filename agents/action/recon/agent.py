# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队侦察 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Asset

SYSTEM_PROMPT = (
    "You are a network reconnaissance agent. Given a target range, "
    "return a JSON object with an 'assets' array. Each asset has "
    "asset_id, host, services (list), os, exposure."
)


class ReconAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def scan(self, target_range: str) -> list[Asset]:
        prompt = f"Scan target range: {target_range}"
        resp = self._provider.complete(
            LLMRequest(
                prompt=prompt,
                model_id="recon-agent",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,
            )
        )
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                Asset(
                    asset_id=a.get("asset_id", ""),
                    host=a.get("host", ""),
                    services=a.get("services", []),
                    os=a.get("os", ""),
                    exposure=a.get("exposure", "external"),
                )
                for a in data.get("assets", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
