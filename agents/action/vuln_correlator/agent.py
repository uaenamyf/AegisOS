# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队漏洞关联 Agent
from __future__ import annotations

import json

from protocol.cyber import Asset, VulnFinding
from agents.tools.llms.base import LLMRequest, ModelProvider

SYSTEM_PROMPT = (
    "You are a vulnerability correlation agent. Given a list of assets, "
    "return JSON with a 'findings' array. Each finding has: finding_id, "
    "cve_id, asset_id, cvss (float), attack_surface."
)


class VulnCorrelatorAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def correlate(self, assets: list[Asset]) -> list[VulnFinding]:
        asset_desc = json.dumps([
            {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
            for a in assets
        ])
        resp = self._provider.complete(LLMRequest(
            prompt=f"Correlate vulnerabilities for these assets: {asset_desc}",
            model_id="vuln-correlator",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
        ))
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                VulnFinding(
                    finding_id=f.get("finding_id", ""),
                    cve_id=f.get("cve_id", ""),
                    asset_id=f.get("asset_id", ""),
                    cvss=f.get("cvss", 0.0),
                    attack_surface=f.get("attack_surface", ""),
                )
                for f in data.get("findings", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
