# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 新建攻防协议类型
"""攻防演练协议类型。

定义网络安全攻防演练场景中使用的数据契约，包括资产、漏洞、
攻击链、告警、防御动作、响应计划及威胁情报等类型。
所有攻防相关的跨模块通信均应使用此处定义的类型。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Asset:
    """网络资产描述。

    表示攻防演练中的一个目标或受保护资产。

    Attributes:
        asset_id: 资产唯一标识。
        host: 主机名或 IP 地址。
        services: 该资产上运行的服务列表。
        os: 操作系统信息。
        exposure: 暴露面分类：external（对外）/ internal（内网）/ isolated（隔离）。
    """

    asset_id: str
    host: str = ""
    services: list = field(default_factory=list)
    os: str = ""
    exposure: str = "external"  # external | internal | isolated


@dataclass
class VulnFinding:
    """漏洞发现记录。

    描述在一次扫描或渗透中发现的漏洞信息。

    Attributes:
        finding_id: 发现记录唯一标识。
        cve_id: 关联的 CVE 编号，无则为空。
        asset_id: 所属资产 ID。
        cvss: CVSS 评分，0.0-10.0。
        attack_surface: 攻击面描述。
    """

    finding_id: str
    cve_id: str = ""
    asset_id: str = ""
    cvss: float = 0.0
    attack_surface: str = ""


@dataclass
class AttackStep:
    """攻击链中的单一步骤。

    描述从源资产到目标资产的一次攻击动作。

    Attributes:
        step_id: 步骤唯一标识。
        technique: 使用的攻击技术（如 MITRE ATT&CK 技术名称）。
        from_asset: 起始资产 ID。
        to_asset: 目标资产 ID。
        success: 该步骤是否执行成功。
    """

    step_id: str
    technique: str = ""
    from_asset: str = ""
    to_asset: str = ""
    success: bool = False


@dataclass
class AttackChain:
    """攻击链。

    由多个 AttackStep 组成的有序攻击路径，描述完整的攻击过程。

    Attributes:
        chain_id: 攻击链唯一标识。
        target: 最终攻击目标。
        steps: 有序的攻击步骤列表。
        status: 攻击链状态：planned / in_progress / completed / failed。
    """

    chain_id: str
    target: str = ""
    steps: list = field(default_factory=list)
    status: str = "planned"

    def to_dict(self) -> dict:
        """将攻击链序列化为字典。

        Returns:
            包含所有字段的字典，steps 子项也会递归转换。
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AttackChain:
        """从字典反序列化攻击链。

        Args:
            data: 包含攻击链字段的字典，其中 steps 为列表 of dict。

        Returns:
            重建后的 AttackChain 实例。
        """
        steps_data = data.pop("steps", [])
        steps = [AttackStep(**s) for s in steps_data]  # 逐个还原步骤子对象
        return cls(steps=steps, **data)


@dataclass
class Alert:
    """安全告警。

    描述检测到的安全事件告警。

    Attributes:
        alert_id: 告警唯一标识。
        severity: 严重程度：low / medium / high / critical。
        src: 告警源（发起方标识）。
        dst: 告警目标（受攻击方标识）。
        technique: 检测到的攻击技术。
        raw: 原始告警数据，保留完整上下文。
    """

    alert_id: str
    severity: str = "low"
    src: str = ""
    dst: str = ""
    technique: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class DefenseAction:
    """防御动作。

    描述针对告警或威胁执行的单项防御操作。

    Attributes:
        action_id: 动作唯一标识。
        kind: 动作类型：monitor / block / isolate / patch / decoy。
        target: 动作作用目标（资产或告警 ID）。
        rationale: 执行该动作的理由说明。
    """

    action_id: str
    kind: str = "monitor"
    target: str = ""
    rationale: str = ""


@dataclass
class ResponsePlan:
    """响应计划。

    针对一组告警生成的防御动作集合，附带置信度与回滚方案。

    Attributes:
        plan_id: 计划唯一标识。
        actions: DefenseAction 列表。
        confidence: 计划置信度，0.0-1.0。
        rollback: 回滚方案，键值对形式描述回滚步骤。
    """

    plan_id: str
    actions: list = field(default_factory=list)
    confidence: float = 0.0
    rollback: dict = field(default_factory=dict)


@dataclass
class ThreatIntel:
    """威胁情报条目。

    描述已知攻击技术与战术的情报信息，供防御决策参考。

    Attributes:
        technique: 攻击技术名称（如 T1059 Command and Scripting Interpreter）。
        tactic: 攻击战术类别（如 Execution / Persistence）。
        refs: 参考资料链接列表。
    """

    technique: str = ""
    tactic: str = ""
    refs: list = field(default_factory=list)
