# date: 2026-08-26
# dev: ox-alpha
"""节点档案与配置契约（R1 —— 端边云任务线）。

定义端(device)/边(edge)/云(cloud)三层节点的统一描述类型 :class:`NodeProfile`，
以及从 ``tooling/configs/infrastructure.yaml`` 加载节点档案的工厂函数。

职责边界：
    - 本模块是**纯数据 + 纯函数**层，不含任何网络 IO；
      网络执行由 R2-R4 的 DeviceNode/EdgeNode/CloudNode 承担。
    - 跨模块传递一律复用 protocol/ 既有契约或本文件类型经
      :meth:`NodeProfile.to_scheduler_model` 桥接为
      ``aegisos_agents/planning/engine/scheduler.Model``。

配置约定：
    - 字符串字段支持 ``${ENV_VAR}`` 插值（os.path.expandvars，跨平台）；
    - 插值后仍含 ``${`` 的节点视为"未配置"，跳过并记录原因，不抛异常——
      保证无 API Key / 无边缘服务器的机器也能加载出可用子集。
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

# 允许做环境变量插值的字符串字段
_ENV_FIELDS = ("base_url", "model_id")

# 仓库默认配置路径：<repo>/tooling/configs/infrastructure.yaml
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "tooling" / "configs" / "infrastructure.yaml"
)


class Tier(StrEnum):
    """节点层级：device=端侧本地算力；edge=边缘服务器；cloud=云端大模型 API。"""

    DEVICE = "device"
    EDGE = "edge"
    CLOUD = "cloud"


class ProviderKind(StrEnum):
    """节点推理后端协议类型。"""

    OLLAMA = "ollama"          # Ollama REST（POST /api/generate），端/边通用
    AEGIS_EDGE = "aegis_edge"  # 自带边缘服务（POST /infer + GET /health）
    OPENAI_API = "openai_api"  # OpenAI 兼容 ChatCompletions（火山 ARK 等）


class PrivacyZone(StrEnum):
    """该层级可承载的数据敏感上限：local > standard > unrestricted。"""

    LOCAL = "local"
    STANDARD = "standard"
    UNRESTRICTED = "unrestricted"


# tier → 默认隐私域（敏感数据留在哪一层的物理语义）
_TIER_PRIVACY: dict[Tier, PrivacyZone] = {
    Tier.DEVICE: PrivacyZone.LOCAL,
    Tier.EDGE: PrivacyZone.STANDARD,
    Tier.CLOUD: PrivacyZone.UNRESTRICTED,
}

# tier → scheduler.Model.size（调度器侧的模型规模标签）
_TIER_SIZE: dict[Tier, str] = {
    Tier.DEVICE: "small",
    Tier.EDGE: "medium",
    Tier.CLOUD: "large",
}


class NodeProfile(BaseModel):
    """单个推理节点的静态档案（注册中心与调度器的公共数据基础）。

    Attributes:
        node_id: 节点唯一标识（如 ``device_local`` / ``edge_server_01``）。
        tier: 所属层级 device | edge | cloud。
        base_url: 推理端点根地址；支持 ``${ENV_VAR}`` 插值。
        provider: 后端协议 ollama | aegis_edge | openai_api。
        model_id: 该节点承载的模型标识（如 ``qwen2.5:0.5b``）。
        capabilities: 能力标签列表（与 scheduler.Model.capabilities 对齐，
            如 chat / reasoning / long_context）。
        privacy_zone: 显式隐私域；缺省时按 tier 推导
            （device→local, edge→standard, cloud→unrestricted）。
        cost_weight: 相对成本权重（token 计费/能耗的粗粒度排序因子，>0）。
        enabled: 是否参与调度；False 时被 select_nodes 过滤。
        timeout_s: 单次推理超时秒数（>0）。
    """

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    node_id: str
    tier: Tier
    base_url: str = ""
    provider: ProviderKind = ProviderKind.OLLAMA
    model_id: str = ""
    capabilities: list[str] = Field(default_factory=lambda: ["chat"])
    privacy_zone: PrivacyZone | None = None
    cost_weight: float = Field(default=1.0, gt=0)
    enabled: bool = True
    timeout_s: float = Field(default=30.0, gt=0)

    @field_validator("node_id")
    @classmethod
    def _node_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("node_id must not be blank")
        return v.strip()

    def resolved_privacy_zone(self) -> PrivacyZone:
        """显式声明优先，否则按层级推导（只升不降语义由调用方保证）。"""
        if self.privacy_zone is not None:
            return PrivacyZone(self.privacy_zone)
        return _TIER_PRIVACY[Tier(self.tier)]

    def to_registry_dict(self) -> dict:
        """投影为 R5 NodeRegistry 注册载荷（online 态由注册中心追加）。"""
        return {
            "node_id": self.node_id,
            "tier": str(self.tier),
            "model_id": self.model_id,
            "capabilities": list(self.capabilities),
            "privacy_zone": self.resolved_privacy_zone().value,
            "enabled": self.enabled,
        }

    def to_scheduler_model(self):
        """桥接为 engine.scheduler.Model（R6 ExecutionDispatcher 的候选形态）。"""
        from aegisos_agents.planning.engine.scheduler.scheduler import Model

        return Model(
            model_id=self.model_id or self.node_id,
            tier=str(self.tier),
            size=_TIER_SIZE[Tier(self.tier)],
            capabilities=list(self.capabilities),
        )


def _expand_env_fields(raw: dict) -> dict:
    """对指定字符串字段做 ${ENV_VAR} 插值，其余字段原样透传。"""
    out = dict(raw)
    for key in _ENV_FIELDS:
        val = out.get(key)
        if isinstance(val, str):
            out[key] = os.path.expandvars(val)
    return out


def _has_unresolved_var(raw: dict) -> bool:
    return any(
        isinstance(raw.get(k), str) and "${" in raw.get(k, "") for k in _ENV_FIELDS
    )


def load_node_profiles(
    path: Path | str | None = None,
) -> tuple[list[NodeProfile], list[str]]:
    """从 YAML 加载节点档案。

    Args:
        path: 配置路径；缺省用仓库内 ``tooling/configs/infrastructure.yaml``。

    Returns:
        (profiles, skipped)：成功加载的档案列表 + 每条跳过原因
        （未配置的环境变量 / 校验失败），保证部分可用即可运行。

    Raises:
        FileNotFoundError: 配置文件不存在。
        ValueError: YAML 顶层结构非法（缺 nodes 映射）。
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"infrastructure config not found: {cfg_path}")

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    nodes_raw = data.get("nodes")
    if not isinstance(nodes_raw, dict) or not nodes_raw:
        raise ValueError(f"'nodes' mapping missing or empty in {cfg_path}")

    profiles: list[NodeProfile] = []
    skipped: list[str] = []
    for node_id, raw in nodes_raw.items():
        fields = _expand_env_fields(dict(raw or {}))
        fields.setdefault("node_id", str(node_id))
        if _has_unresolved_var(fields):
            skipped.append(f"{node_id}: unresolved environment variable (not configured)")
            continue
        try:
            profiles.append(NodeProfile(**fields))
        except ValidationError as exc:
            skipped.append(f"{node_id}: invalid profile ({exc.error_count()} error(s))")
    return profiles, skipped


def select_nodes(
    nodes: list[NodeProfile],
    *,
    tier: Tier | str | None = None,
    capability: str | None = None,
    include_disabled: bool = False,
) -> list[NodeProfile]:
    """按层级 / 能力 / 启用态过滤候选节点（R5/R6 复用的公共查询入口）。"""
    result = nodes
    if tier is not None:
        t = str(tier)
        result = [n for n in result if str(n.tier) == t]
    if capability is not None:
        result = [n for n in result if capability in n.capabilities]
    if not include_disabled:
        result = [n for n in result if n.enabled]
    return result
