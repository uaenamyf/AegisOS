# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 新建攻防协议类型
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Asset:
    asset_id: str
    host: str = ""
    services: list = field(default_factory=list)
    os: str = ""
    exposure: str = "external"  # external | internal | isolated


@dataclass
class VulnFinding:
    finding_id: str
    cve_id: str = ""
    asset_id: str = ""
    cvss: float = 0.0
    attack_surface: str = ""


@dataclass
class AttackStep:
    step_id: str
    technique: str = ""
    from_asset: str = ""
    to_asset: str = ""
    success: bool = False


@dataclass
class AttackChain:
    chain_id: str
    target: str = ""
    steps: list = field(default_factory=list)
    status: str = "planned"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AttackChain:
        steps_data = data.pop("steps", [])
        steps = [AttackStep(**s) for s in steps_data]
        return cls(steps=steps, **data)


@dataclass
class Alert:
    alert_id: str
    severity: str = "low"
    src: str = ""
    dst: str = ""
    technique: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class DefenseAction:
    action_id: str
    kind: str = "monitor"
    target: str = ""
    rationale: str = ""


@dataclass
class ResponsePlan:
    plan_id: str
    actions: list = field(default_factory=list)
    confidence: float = 0.0
    rollback: dict = field(default_factory=dict)


@dataclass
class ThreatIntel:
    technique: str = ""
    tactic: str = ""
    refs: list = field(default_factory=list)
