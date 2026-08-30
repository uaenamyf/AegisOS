# date: 2026-07-05
# dev: myf
"""攻防场景的 MockProvider 包装。

攻防 Agent 会把动态内容（JSON payload）嵌入到 prompt 中，导致精确匹配经常
失败。该包装先尝试精确匹配；若未命中，再回退为前缀匹配预置响应表。
"""

from __future__ import annotations

from aegisos_agents.tools.llms.base import LLMRequest, LLMResponse
from aegisos_agents.tools.llms.mock_provider import MockProvider


def _build_cyber_mock_responses() -> dict[str, str]:
    """预置 MockProvider 的攻防场景 JSON 响应。

    为每个攻防 Agent 的典型 prompt 返回一段结构化的 JSON 文本，覆盖 Recon、
    Detector、VulnCorrelator、ExploitPlanner、LateralMove、Triage、ThreatHunt、
    IRPlanner、Forensics、Critic、Reviewer 等场景。这些响应以 prompt 前缀作为
    键，供 :class:`_CyberMockProvider` 做前缀匹配。

    Returns:
        ``prompt 前缀 -> JSON 响应文本`` 的映射字典。
    """
    import json as _json

    return {
        # --- ReconAgent.scan ---
        "Scan target range: 10.0.0.0/24": _json.dumps(
            {
                "assets": [
                    {
                        "asset_id": "asset-1",
                        "host": "10.0.0.5",
                        "services": ["ssh:22", "http:80"],
                        "os": "Ubuntu 22.04",
                        "exposure": "external",
                    },
                    {
                        "asset_id": "asset-2",
                        "host": "10.0.0.10",
                        "services": ["redis:6379"],
                        "os": "Debian 12",
                        "exposure": "internal",
                    },
                ]
            }
        ),
        # --- DetectorAgent.detect ---
        "Detect anomalies in: ": _json.dumps(
            {
                "alerts": [
                    {
                        "alert_id": "alert-1",
                        "severity": "high",
                        "src": "10.0.0.99",
                        "dst": "10.0.0.5",
                        "technique": "T1110",
                        "raw": {"event": "brute-force"},
                    }
                ]
            }
        ),
        # --- VulnCorrelatorAgent.correlate ---
        "Correlate vulnerabilities for these assets: ": _json.dumps(
            {
                "findings": [
                    {
                        "finding_id": "vuln-1",
                        "cve_id": "CVE-2024-1234",
                        "asset_id": "asset-1",
                        "cvss": 8.1,
                        "attack_surface": "ssh",
                    }
                ]
            }
        ),
        # --- ExploitPlannerAgent.plan ---
        "Plan exploit chain for: ": _json.dumps(
            {
                "chain_id": "chain-1",
                "target": "asset-1",
                "steps": [
                    {
                        "step_id": "step-1",
                        "technique": "T1110",
                        "from_asset": "external",
                        "to_asset": "asset-1",
                        "success": True,
                    }
                ],
                "status": "planned",
            }
        ),
        # --- LateralMoveAgent.plan_moves ---
        "Plan lateral moves. Chain: ": _json.dumps(
            {
                "steps": [
                    {
                        "step_id": "lat-1",
                        "technique": "T1021",
                        "from_asset": "asset-1",
                        "to_asset": "asset-2",
                        "success": True,
                    }
                ]
            }
        ),
        # --- TriageAgent.triage ---
        "Triage these alerts: ": _json.dumps(
            {
                "alerts": [
                    {"alert_id": "alert-1", "severity": "high"},
                ]
            }
        ),
        # --- ThreatHuntAgent.hunt ---
        "Generate hunting hypotheses for: ": _json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis": "Adversary is using stolen credentials for lateral movement",
                        "confidence": 0.82,
                        "technique": "T1078",
                    }
                ]
            }
        ),
        # --- IRPlannerAgent.plan_response ---
        "Plan response for: ": _json.dumps(
            {
                "plan_id": "rp-1",
                "actions": [
                    {
                        "action_id": "act-1",
                        "kind": "isolate",
                        "target": "asset-1",
                        "rationale": "Isolate compromised host",
                    }
                ],
                "confidence": 0.9,
                "rollback": {"enabled": True, "steps": ["reconnect-host", "verify-services"]},
            }
        ),
        # --- ForensicsAgent.investigate ---
        "Investigate: ": _json.dumps(
            {
                "report_id": "forensic-1",
                "root_cause": "SSH brute-force due to weak password policy",
                "timeline": [
                    {"ts": "2026-07-04T10:00Z", "event": "Initial brute-force detected"},
                    {"ts": "2026-07-04T10:05Z", "event": "Successful login from 10.0.0.99"},
                ],
                "recommendations": ["Enforce key-based SSH auth", "Enable fail2ban"],
            }
        ),
        # --- CriticAgent.critique (red side) ---
        "Critique: ": _json.dumps(
            {
                "valid": True,
                "issues": [],
                "severity": "none",
                "suggestion": "Attack chain is valid and follows ATT&CK methodology.",
            }
        ),
        # --- ReviewerAgent.review ---
        "Review consistency: ": _json.dumps(
            {
                "consistent": True,
                "findings": [],
                "overall_assessment": "All artifacts are mutually consistent.",
            }
        ),
    }


class _CyberMockProvider(MockProvider):
    """:class:`MockProvider` 的攻防场景特化，提供基于前缀的 prompt 匹配能力。

    攻防 Agent 会把动态内容（JSON payload）嵌入到 prompt 中，导致精确匹配
    经常失败。先尝试精确匹配；若未命中（响应以 ``[mock]`` 开头或为空），
    再回退为：检查任一预置 key 是否为输入 prompt 的前缀。
    """

    def __init__(self) -> None:
        super().__init__(_build_cyber_mock_responses())

    def complete(self, request: LLMRequest) -> LLMResponse:
        """完成一次 LLM 调用，支持精确匹配与前缀回退。

        Args:
            request: LLM 请求对象，至少包含 ``prompt`` 与 ``model_id``。

        Returns:
            匹配命中的 :class:`LLMResponse`；若均未命中则返回 MockProvider
            的默认 mock 响应。
        """
        # 先尝试精确匹配。
        resp = MockProvider.complete(self, request)
        if resp.ok and resp.text and not resp.text.startswith("[mock]"):
            return resp
        # 回退：对预置 key 做前缀匹配（攻防 prompt 含动态 JSON，需前缀匹配）。
        for key, text in self.responses.items():
            if request.prompt.startswith(key):
                return LLMResponse(
                    text=text,
                    ok=True,
                    model_id=request.model_id or "mock",
                    usage={
                        "prompt_tokens": len(request.prompt) // 4,
                        "completion_tokens": len(text) // 4,
                    },
                )
        # Final fallback: default mock
        return MockProvider.complete(self, request)
