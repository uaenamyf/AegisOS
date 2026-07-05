# date: 2026-07-06
# dev: myf
# changelog: 新建 SDK 结构化输出 Pydantic 类型——11 个攻防 Agent 的 output_type 定义，对应 protocol/cyber.py 的 dataclass
"""SDK 结构化输出 Pydantic 类型 —— 11 个攻防 Agent 的 ``output_type`` 定义。

本模块定义与 ``protocol/cyber.py`` 的 dataclass 对应的 Pydantic ``BaseModel``，
供 SDK ``Agent(output_type=...)`` 使用结构化输出。SDK 会自动：
    - 生成 JSON Schema 注入 prompt
    - 调用 LLM 返回 JSON
    - 用 Pydantic 验证并解析为模型实例
    - 失败时自动重试

迁移完成后，11 个 Agent 中的 ``json.loads + try/except`` 全部删除，
由 SDK 的结构化输出机制替代。

注意：这些 Pydantic 模型与 ``protocol/cyber.py`` 的 dataclass 字段一一对应，
后续 R1 阶段将 protocol 整体迁移到 Pydantic 后，两套类型可合并。当前并存。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssetModel(BaseModel):
    """资产（对应 ``protocol.cyber.Asset``）。"""

    asset_id: str = ""
    host: str = ""
    services: list[str] = Field(default_factory=list)
    os: str = ""
    exposure: str = "external"


class VulnFindingModel(BaseModel):
    """漏洞发现（对应 ``protocol.cyber.VulnFinding``）。"""

    finding_id: str = ""
    cve_id: str = ""
    asset_id: str = ""
    cvss: float = 0.0
    attack_surface: str = ""


class AttackStepModel(BaseModel):
    """攻击步骤（对应 ``protocol.cyber.AttackStep``）。"""

    step_id: str = ""
    technique: str = ""
    from_asset: str = ""
    to_asset: str = ""
    success: bool = False


class AttackChainModel(BaseModel):
    """攻击链（对应 ``protocol.cyber.AttackChain``）。"""

    chain_id: str = ""
    target: str = ""
    steps: list[AttackStepModel] = Field(default_factory=list)
    status: str = "planned"


class AlertModel(BaseModel):
    """告警（对应 ``protocol.cyber.Alert``）。"""

    alert_id: str = ""
    severity: str = "low"
    src: str = ""
    dst: str = ""
    technique: str = ""
    raw: dict[str, object] = Field(default_factory=dict)


class DefenseActionModel(BaseModel):
    """防御动作（对应 ``protocol.cyber.DefenseAction``）。"""

    action_id: str = ""
    kind: str = "monitor"
    target: str = ""
    rationale: str = ""


class ResponsePlanModel(BaseModel):
    """响应计划（对应 ``protocol.cyber.ResponsePlan``）。"""

    plan_id: str = ""
    actions: list[DefenseActionModel] = Field(default_factory=list)
    confidence: float = 0.0
    rollback: dict[str, object] = Field(default_factory=dict)


# ---- Agent 输出聚合类型（每个 Agent 的 output_type）----


class ReconResult(BaseModel):
    """ReconAgent 的结构化输出。"""

    assets: list[AssetModel] = Field(default_factory=list)


class VulnCorrelatorResult(BaseModel):
    """VulnCorrelatorAgent 的结构化输出。"""

    findings: list[VulnFindingModel] = Field(default_factory=list)


class ExploitPlannerResult(BaseModel):
    """ExploitPlannerAgent 的结构化输出。"""

    chain_id: str = ""
    target: str = ""
    steps: list[AttackStepModel] = Field(default_factory=list)
    status: str = "planned"


class LateralMoveResult(BaseModel):
    """LateralMoveAgent 的结构化输出。"""

    steps: list[AttackStepModel] = Field(default_factory=list)


class DetectorResult(BaseModel):
    """DetectorAgent 的结构化输出。"""

    alerts: list[AlertModel] = Field(default_factory=list)


class TriageResult(BaseModel):
    """TriageAgent 的结构化输出（排序后的 alert_id 列表）。"""

    alerts: list[AlertModel] = Field(default_factory=list)


class HuntHypothesisModel(BaseModel):
    """威胁狩猎假设（单条）。"""

    hypothesis: str = ""
    confidence: float = 0.0
    technique: str = ""


class ThreatHuntResult(BaseModel):
    """ThreatHuntAgent 的结构化输出。"""

    hypotheses: list[HuntHypothesisModel] = Field(default_factory=list)


class IRPlannerResult(BaseModel):
    """IRPlannerAgent 的结构化输出。"""

    plan_id: str = ""
    actions: list[DefenseActionModel] = Field(default_factory=list)
    confidence: float = 0.0
    rollback: dict[str, object] = Field(default_factory=dict)


class ForensicsResult(BaseModel):
    """ForensicsAgent 的结构化输出。"""

    report_id: str = ""
    root_cause: str = ""
    timeline: list[dict[str, str]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    """CriticAgent 的结构化输出。"""

    valid: bool = False
    issues: list[str] = Field(default_factory=list)
    severity: str = "none"
    suggestion: str = ""


class ReviewResult(BaseModel):
    """ReviewerAgent 的结构化输出。"""

    consistent: bool = False
    findings: list[str] = Field(default_factory=list)
    overall_assessment: str = ""


__all__ = [
    "AssetModel",
    "VulnFindingModel",
    "AttackStepModel",
    "AttackChainModel",
    "AlertModel",
    "DefenseActionModel",
    "ResponsePlanModel",
    "ReconResult",
    "VulnCorrelatorResult",
    "ExploitPlannerResult",
    "LateralMoveResult",
    "DetectorResult",
    "TriageResult",
    "HuntHypothesisModel",
    "ThreatHuntResult",
    "IRPlannerResult",
    "ForensicsResult",
    "CritiqueResult",
    "ReviewResult",
]
