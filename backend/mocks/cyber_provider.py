# date: 2026-07-05
# dev: myf
"""攻防场景的 MockProvider 包装。

攻防 Agent 会把动态内容（JSON payload）嵌入到 prompt 中，导致精确匹配经常
失败。该包装先尝试精确匹配；若未命中，再回退为前缀匹配预置响应表。
"""
from __future__ import annotations

from aegisos_agents.tools.llms.base import LLMRequest, LLMResponse
from aegisos_agents.tools.llms.mock_provider import MockProvider


# 蓝队场景表：ATT&CK 技法 → (严重度, 告警事件, 威胁假设, 响应动作列表, 回滚步骤)
# kind 合法值：monitor | block | isolate | patch | decoy（见 protocol/cyber.py DefenseAction）
_BLUE_SCENARIOS: dict[str, dict] = {
    "T1110": {
        "severity": "high",
        "alert_event": "brute-force",
        "hypothesis": "Adversary is brute-forcing credentials to gain initial access",
        "actions": [
            {"kind": "block", "target": "src-ip", "rationale": "Block source IP performing credential brute-force"},
            {"kind": "patch", "target": "auth-policy", "rationale": "Enforce account lockout and rate limiting"},
            {"kind": "monitor", "target": "auth-logs", "rationale": "Watch for further login attempts"},
        ],
        "rollback": ["unblock-src-ip", "relax-lockout-policy"],
    },
    "T1078": {
        "severity": "high",
        "alert_event": "valid-accounts",
        "hypothesis": "Adversary is using stolen valid credentials for lateral movement",
        "actions": [
            {"kind": "isolate", "target": "compromised-host", "rationale": "Isolate host with anomalous authenticated sessions"},
            {"kind": "block", "target": "anomalous-login-src", "rationale": "Block source of anomalous logins"},
            {"kind": "patch", "target": "credential-hygiene", "rationale": "Rotate credentials and enforce MFA"},
        ],
        "rollback": ["reconnect-host", "verify-services"],
    },
    "T1566": {
        "severity": "medium",
        "alert_event": "phishing",
        "hypothesis": "Adversary delivered a phishing payload to end users",
        "actions": [
            {"kind": "block", "target": "sender-domain", "rationale": "Block phishing sender domain at mail gateway"},
            {"kind": "decoy", "target": "mailbox-honeypot", "rationale": "Deploy decoy mailbox to profile attacker behavior"},
            {"kind": "monitor", "target": "endpoints", "rationale": "Monitor endpoints for payload execution"},
        ],
        "rollback": ["release-quarantined-mail"],
    },
    "T1036": {
        "severity": "medium",
        "alert_event": "masquerading",
        "hypothesis": "Adversary is masquerading as a legitimate process to evade detection",
        "actions": [
            {"kind": "isolate", "target": "affected-host", "rationale": "Isolate host running masquerading process"},
            {"kind": "patch", "target": "edr-rules", "rationale": "Update EDR allowlist with new behavioral rules"},
            {"kind": "monitor", "target": "process-tree", "rationale": "Monitor process creation chain"},
        ],
        "rollback": ["reconnect-host", "verify-process-inventory"],
    },
    "T1059": {
        "severity": "high",
        "alert_event": "command-execution",
        "hypothesis": "Adversary achieved remote command execution on a host",
        "actions": [
            {"kind": "block", "target": "c2-domain", "rationale": "Block command-and-control domain at perimeter"},
            {"kind": "patch", "target": "exploited-service", "rationale": "Patch the exploited service immediately"},
            {"kind": "isolate", "target": "affected-host", "rationale": "Isolate affected host pending forensic review"},
        ],
        "rollback": ["reconnect-host", "verify-patch-deployed"],
    },
    "T1021": {
        "severity": "high",
        "alert_event": "lateral-movement",
        "hypothesis": "Adversary is moving laterally across the internal network",
        "actions": [
            {"kind": "isolate", "target": "pivot-hosts", "rationale": "Isolate compromised pivot hosts"},
            {"kind": "block", "target": "lateral-segment", "rationale": "Block inter-segment traffic from compromised zone"},
            {"kind": "monitor", "target": "network-flow", "rationale": "Monitor remaining hosts for beaconing"},
        ],
        "rollback": ["restore-segment-routing"],
    },
    "T1496": {
        "severity": "medium",
        "alert_event": "resource-hijacking",
        "hypothesis": "Adversary is hijacking compute resources for cryptomining",
        "actions": [
            {"kind": "patch", "target": "vulnerable-service", "rationale": "Patch the service exploited to deploy miner"},
            {"kind": "block", "target": "mining-pool", "rationale": "Block mining pool communication at egress"},
            {"kind": "monitor", "target": "cpu-metrics", "rationale": "Monitor CPU utilization for miner re-infection"},
        ],
        "rollback": ["allow-egress-after-review"],
    },
    "T1505": {
        "severity": "high",
        "alert_event": "webshell",
        "hypothesis": "Adversary implanted a webshell on the web server",
        "actions": [
            {"kind": "isolate", "target": "web-server", "rationale": "Isolate web server hosting the webshell"},
            {"kind": "patch", "target": "webshell-artifact", "rationale": "Remove webshell artifact and harden upload path"},
            {"kind": "monitor", "target": "web-logs", "rationale": "Audit web access logs for re-exploitation"},
        ],
        "rollback": ["reconnect-web-server", "verify-web-service"],
    },
    "T1190": {
        "severity": "high",
        "alert_event": "exploit-public-facing",
        "hypothesis": "Adversary is exploiting a public-facing application vulnerability",
        "actions": [
            {"kind": "block", "target": "attacker-src", "rationale": "Block attacker source at WAF"},
            {"kind": "patch", "target": "public-app", "rationale": "Apply vendor patch to public-facing application"},
            {"kind": "monitor", "target": "waf-logs", "rationale": "Monitor WAF logs for follow-up attempts"},
        ],
        "rollback": ["release-waf-block"],
    },
    "T1046": {
        "severity": "low",
        "alert_event": "port-scan",
        "hypothesis": "Adversary is scanning the network to map the attack surface",
        "actions": [
            {"kind": "monitor", "target": "network-flow", "rationale": "Log and monitor scan source for follow-up activity"},
            {"kind": "block", "target": "scanner-src", "rationale": "Rate-limit or block aggressive scanner source"},
            {"kind": "patch", "target": "exposed-services", "rationale": "Harden exposed services discovered by the scan"},
        ],
        "rollback": ["release-scanner-block"],
    },
    "T1210": {
        "severity": "high",
        "alert_event": "exploit-remote-services",
        "hypothesis": "Adversary is exploiting remote services to move deeper into the network",
        "actions": [
            {"kind": "isolate", "target": "target-service-host", "rationale": "Isolate host running the exploited remote service"},
            {"kind": "patch", "target": "remote-service", "rationale": "Patch the exploited remote service and restrict exposure"},
            {"kind": "monitor", "target": "service-logs", "rationale": "Audit remote service logs for re-exploitation"},
        ],
        "rollback": ["reconnect-host", "verify-service-patch"],
    },
}

# 自由文本技法别名 → ATT&CK 编号
_TECHNIQUE_ALIASES: dict[str, str] = {
    "brute-force": "T1110",
    "bruteforce": "T1110",
    "brute": "T1110",
    "ssh-brute-force": "T1110",
    "sshbruteforce": "T1110",
    "valid-accounts": "T1078",
    "validaccounts": "T1078",
    "credentials": "T1078",
    "phishing": "T1566",
    "masquerading": "T1036",
    "masquerade": "T1036",
    "command-execution": "T1059",
    "commandexecution": "T1059",
    "rce": "T1059",
    "lateral-movement": "T1021",
    "lateralmovement": "T1021",
    "lateral": "T1021",
    "resource-hijacking": "T1496",
    "cryptomining": "T1496",
    "mining": "T1496",
    "webshell": "T1505",
    "web-shell": "T1505",
    "exploit-public-facing": "T1190",
    "exploit": "T1190",
    "port-scan": "T1046",
    "portscan": "T1046",
    "network-service-scanning": "T1046",
}


def _normalize_technique(value: str) -> str | None:
    """把技法文本规整为 ATT&CK 编号；无法识别返回 None。"""
    if not value:
        return None
    v = str(value).strip()
    # 1) 精确 ATT&CK 编号
    if v.upper() in _BLUE_SCENARIOS:
        return v.upper()
    # 2) 别名表精确匹配
    key = v.lower().replace(" ", "-")
    if key in _TECHNIQUE_ALIASES:
        return _TECHNIQUE_ALIASES[key]
    # 3) 去分隔符后的包含匹配（ssh-brute-force → brute-force → T1110）
    compact = v.lower().replace("-", "").replace("_", "").replace(" ", "")
    for alias, tid in _TECHNIQUE_ALIASES.items():
        alias_compact = alias.replace("-", "").replace("_", "").replace(" ", "")
        if alias_compact and alias_compact in compact:
            return tid
    return None


def _extract_technique(payload: object) -> str | None:
    """从事件流/告警/假设负载里提取第一个可识别的技法编号。"""
    hits = _extract_techniques(payload)
    return hits[0] if hits else None


def _extract_techniques(payload: object, limit: int = 3) -> list[str]:
    """从负载里提取去重保序的技法编号列表（最多 ``limit`` 个）。

    事件流/告警/假设里可能包含多个 ATT&CK 技法（多步攻击链），按出现顺序
    去重返回，供蓝队 mock 生成多告警/多假设/复合动作。
    """
    items = payload if isinstance(payload, list) else [payload]
    out: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for field in ("technique", "event", "event_type", "type", "action"):
            hit = _normalize_technique(str(item.get(field, "")))
            if hit and hit not in out:
                out.append(hit)
                if len(out) >= limit:
                    return out
        raw = item.get("raw")
        if isinstance(raw, dict):
            for field in ("technique", "event", "type"):
                hit = _normalize_technique(str(raw.get(field, "")))
                if hit and hit not in out:
                    out.append(hit)
                    if len(out) >= limit:
                        return out
    return out


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
                    {
                        "asset_id": "asset-3",
                        "host": "10.0.0.15",
                        "services": ["mysql:3306", "ftp:21"],
                        "os": "CentOS 7",
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
                        "cve_id": "CVE-2021-3156",
                        "asset_id": "asset-1",
                        "cvss": 7.8,
                        "attack_surface": "ssh",
                    },
                    {
                        "finding_id": "vuln-2",
                        "cve_id": "CVE-2021-41773",
                        "asset_id": "asset-1",
                        "cvss": 7.5,
                        "attack_surface": "http",
                    },
                    {
                        "finding_id": "vuln-3",
                        "cve_id": "CVE-2022-0543",
                        "asset_id": "asset-2",
                        "cvss": 9.8,
                        "attack_surface": "redis",
                    },
                    {
                        "finding_id": "vuln-4",
                        "cve_id": "CVE-2021-4034",
                        "asset_id": "asset-3",
                        "cvss": 7.8,
                        "attack_surface": "ftp",
                    },
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
                    },
                    {
                        "step_id": "step-2",
                        "technique": "T1059",
                        "from_asset": "asset-1",
                        "to_asset": "asset-2",
                        "success": True,
                    },
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
                    },
                    {
                        "step_id": "lat-2",
                        "technique": "T1210",
                        "from_asset": "asset-1",
                        "to_asset": "asset-3",
                        "success": True,
                    },
                ]
            }
        ),
        # --- TriageAgent.triage ---
        "Triage these alerts: ": _json.dumps(
            {
                "alerts": [
                    {
                        "alert_id": "alert-1",
                        "severity": "high",
                        "src": "10.0.0.99",
                        "dst": "10.0.0.5",
                        "technique": "T1110",
                        "raw": {"event": "brute-force"},
                    },
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
        """侦察演化：round>=2 时才暴露高价值内部资产 asset-4（关键业务/域控）。"""
        import json as _json

        if round_no < 2:
            return base_text
        data = _json.loads(base_text)
        existing = {a["asset_id"] for a in data["assets"]}
        if "asset-4" not in existing:
            data["assets"] = data["assets"] + [
                {
                    "asset_id": "asset-4",
                    "host": "10.0.0.20",
                    "services": ["ssh:22", "rdp:3389"],
                    "os": "Windows Server 2019",
                    "exposure": "internal",
                }
            ]
        return _json.dumps(data)

    def _evolve_exploit(self, base_text: str, round_no: int) -> str:
        """利用链演化：round>=2 时红队针对新暴露资产 asset-4 追加利用步骤。"""
        import json as _json

        if round_no < 2:
            return base_text
        data = _json.loads(base_text)
        existing = {s["step_id"] for s in data["steps"]}
        if "step-3" not in existing:
            data["steps"] = data["steps"] + [
                {
                    "step_id": "step-3",
                    "technique": "T1078",
                    "from_asset": "asset-2",
                    "to_asset": "asset-4",
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
                        "攻击链未覆盖内部高价值资产 asset-4（10.0.0.20:rdp 关键业务入口），需补充利用步骤再评估"
                    ],
                    "severity": "high",
                    "suggestion": "补充对 asset-4 的利用路径后重新校验",
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

    # ---- R9: 蓝队 mock 上下文感知演化（detector → threat_hunt → ir_planner）----
    # 修复：蓝队链路不再返回固定静态响应，而是根据输入事件流/告警/假设中的
    # ATT&CK 技法映射到不同告警、假设与响应动作组合，驱动演示真实多变。

    @staticmethod
    def _payload_from_prompt(prompt: str, prefix: str) -> object | None:
        """从 prompt 中截取前缀之后的 JSON 负载并解析。"""
        import json as _json

        raw = prompt[len(prefix):].strip()
        if not raw:
            return None
        try:
            return _json.loads(raw)
        except Exception:  # noqa: BLE001
            return None

    def _evolve_detector(self, base_text: str, prompt: str, prefix: str) -> str:
        """入侵检测演化：按事件流中的技法输出对应告警（支持多技法多告警）。"""
        import json as _json

        payload = self._payload_from_prompt(prompt, prefix)
        techniques = _extract_techniques(payload)
        if not techniques:
            return base_text
        items = payload if isinstance(payload, list) else [payload]
        alerts = []
        for i, technique in enumerate(techniques):
            scen = _BLUE_SCENARIOS[technique]
            item = items[i] if i < len(items) and isinstance(items[i], dict) else {}
            src = (
                item.get("src_ip")
                or item.get("src")
                or item.get("source")
                or "10.0.0.99"
            )
            dst = item.get("dst_ip") or item.get("dst") or item.get("target") or "10.0.0.5"
            alerts.append(
                {
                    "alert_id": f"alert-{i + 1}",
                    "severity": scen["severity"],
                    "src": src,
                    "dst": dst,
                    "technique": technique,
                    "raw": {"event": scen["alert_event"], "technique": technique},
                }
            )
        return _json.dumps({"alerts": alerts})

    def _evolve_threat_hunt(self, base_text: str, prompt: str, prefix: str) -> str:
        """威胁狩猎演化：按告警中的技法生成对应假设（支持多技法多假设）。"""
        import json as _json

        payload = self._payload_from_prompt(prompt, prefix)
        techniques = _extract_techniques(payload)
        if not techniques:
            return base_text
        hypotheses = [
            {
                "hypothesis": _BLUE_SCENARIOS[t]["hypothesis"],
                "confidence": 0.82,
                "technique": t,
            }
            for t in techniques
        ]
        return _json.dumps({"hypotheses": hypotheses})

    def _evolve_ir_planner(self, base_text: str, prompt: str, prefix: str) -> str:
        """响应规划演化：按威胁假设中的技法生成多动作响应计划（多技法合并去重）。"""
        import json as _json

        payload = self._payload_from_prompt(prompt, prefix)
        techniques = _extract_techniques(payload)
        if not techniques:
            return base_text
        actions: list[dict] = []
        seen: set[tuple] = set()
        for technique in techniques:
            scen = _BLUE_SCENARIOS[technique]
            for a in scen["actions"]:
                dedup_key = (a["kind"], a["target"])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                actions.append(
                    {
                        "action_id": f"act-{len(actions) + 1}",
                        **a,
                    }
                )
        rollback_steps = []
        seen_rollback: set[str] = set()
        for technique in techniques:
            for step in _BLUE_SCENARIOS[technique]["rollback"]:
                if step in seen_rollback:
                    continue
                seen_rollback.add(step)
                rollback_steps.append(step)
        return _json.dumps(
            {
                "plan_id": "rp-" + "-".join(t.lower() for t in techniques),
                "actions": actions,
                "confidence": 0.9,
                "rollback": {
                    "enabled": True,
                    "steps": rollback_steps,
                },
            }
        )

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
                elif request.prompt.startswith("Detect anomalies in: "):
                    text = self._evolve_detector(text, request.prompt, "Detect anomalies in: ")
                elif request.prompt.startswith("Generate hunting hypotheses for: "):
                    text = self._evolve_threat_hunt(
                        text, request.prompt, "Generate hunting hypotheses for: "
                    )
                elif request.prompt.startswith("Plan response for: "):
                    text = self._evolve_ir_planner(text, request.prompt, "Plan response for: ")
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
