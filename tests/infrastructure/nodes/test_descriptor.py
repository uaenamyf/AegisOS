"""R1 节点档案与配置契约 —— 单元测试。

覆盖：NodeProfile 校验 / YAML 加载与环境变量插值 / 注册投影 /
scheduler.Model 桥接 / 过滤辅助函数 / 真实配置文件冒烟。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from infrastructure.nodes.descriptor import (
    NodeProfile,
    ProviderKind,
    Tier,
    load_node_profiles,
    select_nodes,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_device(**overrides) -> NodeProfile:
    base = dict(
        node_id="device_test",
        tier=Tier.DEVICE,
        base_url="http://localhost:11434",
        provider=ProviderKind.OLLAMA,
        model_id="qwen2.5:0.5b",
        capabilities=["chat"],
        cost_weight=0.1,
    )
    base.update(overrides)
    return NodeProfile(**base)


# ---------- 构造与校验 ----------


def test_valid_profile_construction():
    p = _make_device()
    assert p.node_id == "device_test"
    assert p.tier == Tier.DEVICE
    assert p.enabled is True


def test_invalid_tier_rejected():
    with pytest.raises(ValidationError):
        _make_device(tier="laptop")


def test_invalid_provider_rejected():
    with pytest.raises(ValidationError):
        _make_device(provider="magic")


def test_blank_node_id_rejected():
    with pytest.raises(ValidationError):
        _make_device(node_id="  ")


def test_cost_weight_must_be_positive():
    with pytest.raises(ValidationError):
        _make_device(cost_weight=0)


def test_privacy_zone_derived_from_tier():
    assert _make_device(tier=Tier.DEVICE).resolved_privacy_zone().value == "local"
    edge = _make_device(node_id="e", tier=Tier.EDGE)
    assert edge.resolved_privacy_zone().value == "standard"
    cloud = _make_device(node_id="c", tier=Tier.CLOUD)
    assert cloud.resolved_privacy_zone().value == "unrestricted"


def test_explicit_privacy_zone_overrides_derivation():
    cloud = _make_device(node_id="c", tier=Tier.CLOUD, privacy_zone="local")
    assert cloud.resolved_privacy_zone().value == "local"


# ---------- YAML 加载 ----------


def test_load_profiles_from_yaml(tmp_path: Path):
    yaml_file = tmp_path / "infra.yaml"
    yaml_file.write_text(
        """
nodes:
  device_a:
    tier: device
    base_url: http://localhost:11434
    provider: ollama
    model_id: tiny
    capabilities: [chat]
    cost_weight: 0.1
  edge_b:
    tier: edge
    base_url: http://10.0.0.2:8900
    provider: ollama
    model_id: medium
    capabilities: [chat, reasoning]
""",
        encoding="utf-8",
    )
    profiles, skipped = load_node_profiles(yaml_file)
    assert skipped == []
    ids = {p.node_id for p in profiles}
    assert ids == {"device_a", "edge_b"}
    edge = next(p for p in profiles if p.tier == Tier.EDGE)
    assert edge.capabilities == ["chat", "reasoning"]
    assert edge.cost_weight == 1.0


def test_env_interpolation_resolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AEGIS_TEST_EDGE_URL", "http://10.1.1.9:8900")
    yaml_file = tmp_path / "infra.yaml"
    yaml_file.write_text(
        """
nodes:
  edge_env:
    tier: edge
    base_url: ${AEGIS_TEST_EDGE_URL}
    provider: ollama
    model_id: medium
""",
        encoding="utf-8",
    )
    profiles, skipped = load_node_profiles(yaml_file)
    assert skipped == []
    assert profiles[0].base_url == "http://10.1.1.9:8900"


def test_unresolved_env_node_skipped_with_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("AEGIS_TEST_MISSING_VAR", raising=False)
    yaml_file = tmp_path / "infra.yaml"
    yaml_file.write_text(
        """
nodes:
  ghost:
    tier: edge
    base_url: ${AEGIS_TEST_MISSING_VAR}
    provider: ollama
    model_id: m
  solid:
    tier: device
    base_url: http://localhost:11434
    provider: ollama
    model_id: tiny
""",
        encoding="utf-8",
    )
    profiles, skipped = load_node_profiles(yaml_file)
    assert [p.node_id for p in profiles] == ["solid"]
    assert len(skipped) == 1 and "ghost" in skipped[0]


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_node_profiles(tmp_path / "nope.yaml")


def test_real_repo_config_smoke():
    """仓库自带 infrastructure.yaml 必须至少给出端侧节点且全部合法。"""
    profiles, _skipped = load_node_profiles()
    assert any(p.tier == Tier.DEVICE for p in profiles)
    assert all(p.tier in (Tier.DEVICE, Tier.EDGE, Tier.CLOUD) for p in profiles)


# ---------- 投影与桥接 ----------


def test_to_registry_dict_projection_shape():
    d = _make_device().to_registry_dict()
    assert set(d.keys()) == {
        "node_id",
        "tier",
        "model_id",
        "capabilities",
        "privacy_zone",
        "enabled",
    }
    assert d["tier"] == "device"


def test_to_scheduler_model_bridge():
    dev = _make_device()
    m = dev.to_scheduler_model()
    assert m.model_id == "qwen2.5:0.5b"
    assert m.tier == "device"
    assert m.size == "small"
    assert "chat" in m.capabilities

    cloud = _make_device(node_id="c", tier=Tier.CLOUD, capabilities=["reasoning"])
    mc = cloud.to_scheduler_model()
    assert mc.size == "large"


# ---------- 过滤辅助 ----------


def test_select_nodes_filters():
    nodes = [
        _make_device(),
        _make_device(node_id="e", tier=Tier.EDGE, capabilities=["chat", "reasoning"]),
        _make_device(node_id="off", enabled=False),
    ]
    assert [n.node_id for n in select_nodes(nodes, tier=Tier.EDGE)] == ["e"]
    assert [n.node_id for n in select_nodes(nodes, capability="reasoning")] == ["e"]
    assert len(select_nodes(nodes, include_disabled=True)) == 3
    assert len(select_nodes(nodes)) == 2
