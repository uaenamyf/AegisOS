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

    # ---- R1.5: 按轮演化的轮次上下文解析与响应合成 ----
    @staticmethod
    def _round_from_prompt(prompt: str) -> int:
        """从 prompt 中解析 ``[round=N]`` 标记；无标记返回 0。"""
        import re

        m = re.search(r"\[round=(\d+)\]", prompt)
        return int(m.group(1)) if m else 0

    def _evolve_recon(self, base_text: str, round_no: int) -> str:
        """侦察演化：round>=2 时才暴露高风险内部资产 asset-3。"""
        import json as _json

        if round_no < 2:
            return base_text
        data = _json.loads(base_text)
        data["assets"] = data["assets"] + [
            {
                "asset_id": "asset-3",
                "host": "10.0.0.15",
                "services": ["redis:6379"],
                "os": "Ubuntu 20.04",
                "exposure": "internal",
            }
        ]
        return _json.dumps(data)

    def _evolve_exploit(self, base_text: str, round_no: int) -> str:
        """利用链演化：round>=2 时红队针对新资产 asset-3 追加利用步骤 step-2。"""
        import json as _json

        if round_no < 2:
            return base_text
        data = _json.loads(base_text)
        data["steps"] = data["steps"] + [
            {
                "step_id": "step-2",
                "technique": "T1210",
                "from_asset": "asset-1",
                "to_asset": "asset-3",
                "success": True,
            }
        ]
        return _json.dumps(data)

    def _evolve_critic(self, base_text: str, round_no: int) -> str:
        """紫队批判演化：round=1 留缺口(valid=False)，>=2 补齐(valid=True)。"""
        import json as _json

        if round_no <= 0:
            return base_text
        data = _json.loads(base_text)
        if round_no == 1:
            data.update(
                {
                    "valid": False,
                    "issues": [
                        "攻击链未覆盖内部资产 asset-3（10.0.0.15:redis 高危入口），需补充利用步骤再评估"
                    ],
                    "severity": "high",
                    "suggestion": "补充对 asset-3 的利用路径后重新校验",
                }
            )
        else:
            data.update(
                {
                    "valid": True,
                    "issues": [],
                    "severity": "none",
                    "suggestion": "攻击链已覆盖全部暴露面并通过 ATT&CK 映射校验。",
                }
            )
        return _json.dumps(data)

    def complete(self, request: LLMRequest) -> LLMResponse:
        """完成一次 LLM 调用，支持精确匹配与前缀回退。

        R1.5：命中前缀后，若 prompt 带 ``[round=N]`` 标记，则按轮次套用
        演化响应（侦察/利用链/紫队批判），驱动多轮收敛演练真实可演示；
        无标记或 round<2 时完全回退旧静态响应，保证既有调用零破坏。

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
                round_no = self._round_from_prompt(request.prompt)
                if request.prompt.startswith("Scan target range:"):
                    text = self._evolve_recon(text, round_no)
                elif request.prompt.startswith("Plan exploit chain for:"):
                    text = self._evolve_exploit(text, round_no)
                elif request.prompt.startswith("Critique: "):
                    text = self._evolve_critic(text, round_no)
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
