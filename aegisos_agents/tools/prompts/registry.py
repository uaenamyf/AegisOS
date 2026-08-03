# date: 2026-08-03
# dev: 123 chen
"""Prompt 模板注册中心 —— 集中管理所有 Agent 的 SYSTEM_PROMPT。

提供模板注册、版本追踪、角色筛选、版本回滚功能。
预置 11 个攻防 Agent 的默认模板（从各 Agent SYSTEM_PROMPT 提取）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    """Prompt 模板条目。

    Attributes:
        name: 模板名称（如 ``recon``）。
        version: 版本号（注册时自动递增）。
        role: 角色阵营（red / blue / purple）。
        content: 模板正文，支持 ``{{ var }}`` 占位符。
        variables: 模板中使用的变量名列表。
        created_at: 创建时间戳（monotonic）。
    """

    name: str = ""
    version: int = 1
    role: str = "red"
    content: str = ""
    variables: list[str] = field(default_factory=list)
    created_at: float = 0.0


# 预置模板（从各 Agent SYSTEM_PROMPT 提取）
_BUILTIN_TEMPLATES: list[dict] = [
    {
        "name": "recon",
        "role": "red",
        "content": (
            "You are a network reconnaissance agent. Given a target range, "
            "return a JSON object with an 'assets' array. Each asset has "
            "asset_id, host, services (list), os, exposure."
        ),
        "variables": ["target_range"],
    },
    {
        "name": "vuln_correlator",
        "role": "red",
        "content": (
            "You are a vulnerability correlation agent. Given a list of assets, "
            "identify vulnerabilities by matching services/OS against known CVE/ATT&CK "
            "techniques. Return a JSON object with a 'findings' array."
        ),
        "variables": ["assets"],
    },
    {
        "name": "exploit_planner",
        "role": "red",
        "content": (
            "You are an exploit planning agent. Given a list of vulnerability findings, "
            "design an attack chain from initial access to objective. Return attack_chain_id, "
            "steps (list of AttackStep), estimated_time."
        ),
        "variables": ["findings", "target_objective"],
    },
    {
        "name": "lateral_move",
        "role": "red",
        "content": (
            "You are a lateral movement agent. Given an attack chain and network topology, "
            "plan lateral movement steps between compromised and target hosts. Return steps "
            "with source, target, technique, and estimated_success_rate."
        ),
        "variables": ["attack_chain", "topology"],
    },
    {
        "name": "detector",
        "role": "blue",
        "content": (
            "You are a threat detection agent. Analyze event streams for indicators of "
            "compromise (IOCs) and suspicious behavior patterns. Return alerts with "
            "alert_id, severity, description, affected_asset, and technique_id."
        ),
        "variables": ["event_stream"],
    },
    {
        "name": "triage",
        "role": "blue",
        "content": (
            "You are an alert triage agent. Prioritize alerts by severity, impact, and "
            "urgency. Return prioritized alerts with priority score, justification, "
            "and recommended action."
        ),
        "variables": ["alerts"],
    },
    {
        "name": "threat_hunt",
        "role": "blue",
        "content": (
            "You are a threat hunting agent. Given prioritized alerts and ATT&CK knowledge, "
            "generate hunt hypotheses: possible attack scenarios, affected systems, "
            "recommended investigation steps."
        ),
        "variables": ["alerts"],
    },
    {
        "name": "ir_planner",
        "role": "blue",
        "content": (
            "You are an incident response planning agent. Given threat hunt hypotheses, "
            "create a response plan with containment, eradication, recovery, and "
            "lessons-learned sections. Return plan_id and step list."
        ),
        "variables": ["hypotheses"],
    },
    {
        "name": "forensics",
        "role": "blue",
        "content": (
            "You are a forensic investigation agent. Investigate the incident based on "
            "the response plan execution results. Return a forensic report with timeline, "
            "root cause, affected systems, evidence summary."
        ),
        "variables": ["response_plan"],
    },
    {
        "name": "critic_red",
        "role": "purple",
        "content": (
            "You are a red team critic. Review the attack chain for realism, completeness, "
            "and effectiveness. Identify missing steps, unrealistic assumptions, "
            "and countermeasures the blue team might deploy."
        ),
        "variables": ["attack_chain"],
    },
    {
        "name": "critic_blue",
        "role": "purple",
        "content": (
            "You are a blue team critic. Review the defense response for gaps, "
            "missed detections, and response effectiveness. Suggest improvements "
            "to detection rules and response procedures."
        ),
        "variables": ["response_plan", "alerts"],
    },
    {
        "name": "reviewer",
        "role": "purple",
        "content": (
            "You are a defense reviewer. Cross-validate red and blue team outputs "
            "for consistency and accuracy. Provide a summary assessment with agreement "
            "level and identified discrepancies."
        ),
        "variables": ["red_output", "blue_output"],
    },
]


class PromptRegistry:
    """Prompt 模板注册中心。

    集中管理所有 Agent 的 SYSTEM_PROMPT 模板，支持：
        - 按名称注册（同名校验 → 版本自动递增）
        - 按名称+版本号精确查询
        - 按角色（red/blue/purple）筛选
        - 版本回滚

    Attributes:
        _templates: {name -> [PromptTemplate]} 版本历史列表（按版本号升序）。
    """

    def __init__(self, seed: bool = True) -> None:
        """初始化注册中心。

        Args:
            seed: 是否预置 11 个 Agent 默认模板，默认 True。
        """
        self._templates: dict[str, list[PromptTemplate]] = {}
        if seed:
            self._seed_builtins()

    # ---- 公开接口 ----

    def register(
        self,
        name: str,
        content: str,
        role: str = "red",
        variables: list[str] | None = None,
    ) -> int:
        """注册一个 Prompt 模板，自动递增版本号。

        Args:
            name: 模板名称。
            content: 模板正文。
            role: 角色阵营（red/blue/purple）。
            variables: 变量名列表。

        Returns:
            新版本号。
        """
        history = self._templates.setdefault(name, [])
        version = len(history) + 1
        tpl = PromptTemplate(
            name=name,
            version=version,
            role=role,
            content=content,
            variables=variables or [],
            created_at=time.monotonic(),
        )
        history.append(tpl)
        return version

    def get(self, name: str, version: int | None = None) -> PromptTemplate | None:
        """查询模板。version 为 None 时返回最新版本。

        Args:
            name: 模板名称。
            version: 版本号，None 表示最新。

        Returns:
            PromptTemplate 或 None。
        """
        history = self._templates.get(name)
        if not history:
            return None
        if version is None:
            return history[-1]
        for tpl in history:
            if tpl.version == version:
                return tpl
        return None

    def list_all(self) -> list[PromptTemplate]:
        """列举所有模板（每名称取最新版本）。"""
        return [h[-1] for h in self._templates.values()]

    def list_by_role(self, role: str) -> list[PromptTemplate]:
        """按角色筛选模板（每名称取最新版本）。

        Args:
            role: 角色阵营（red/blue/purple）。

        Returns:
            匹配的模板列表。
        """
        return [h[-1] for h in self._templates.values() if h[-1].role == role]

    def rollback(self, name: str, version: int) -> PromptTemplate | None:
        """回滚到指定版本（将目标版本复制为新版本）。

        Args:
            name: 模板名称。
            version: 目标版本号。

        Returns:
            新创建的 PromptTemplate（最新版本）；不存在时返回 None。
        """
        target = self.get(name, version)
        if target is None:
            return None
        return PromptTemplate(
            name=name,
            version=self.register(name, target.content, target.role, list(target.variables)),
            role=target.role,
            content=target.content,
            variables=list(target.variables),
            created_at=time.monotonic(),
        )

    def history(self, name: str) -> list[PromptTemplate]:
        """获取模板的完整版本历史。

        Args:
            name: 模板名称。

        Returns:
            版本历史列表（按版本号升序）。
        """
        return list(self._templates.get(name, []))

    # ---- 私有 ----

    def _seed_builtins(self) -> None:
        """预置 11 个 Agent 默认模板。"""
        for t in _BUILTIN_TEMPLATES:
            self.register(
                name=t["name"],
                content=t["content"],
                role=t.get("role", "red"),
                variables=t.get("variables", []),
            )
