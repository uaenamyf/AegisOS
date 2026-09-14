# date: 2026-09-14
# dev: OpenSquilla
"""R22 端边云实时路由决策测试 —— 验证路由不再只由 agent 名决定。

覆盖三个"实时"因子：
    1. 数据敏感等级：同一 agent，prompt 含 IP/CVE 时禁止落云（紫队 cloud→edge）；
    2. 节点健康度：某层节点连续失败时避让到次近健康层；
    3. 在线拓扑：候选层离线时自动降级（R20 既有行为回归）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aegisos_agents.tools.llms.sdk_provider import RoutedSDKModel


class _FakeFallback:
    model = "fake-model"
    _client = None


def _registry(nodes: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(snapshot=lambda: nodes)


def _model_with(registry: SimpleNamespace) -> RoutedSDKModel:
    routed = RoutedSDKModel(_FakeFallback(), registry=registry)  # type: ignore[arg-type]
    return routed


_FULL_ONLINE = [
    {"node_id": "device_local", "tier": "device", "status": "online", "model_id": "m", "consecutive_failures": 0, "base_url": "https://x/api"},
    {"node_id": "edge_server_01", "tier": "edge", "status": "online", "model_id": "m", "consecutive_failures": 0, "base_url": "https://x/api"},
    {"node_id": "cloud_api", "tier": "cloud", "status": "online", "model_id": "m", "consecutive_failures": 0, "base_url": "https://x/api"},
]


class TestRealtimePrivacyRouting:
    def test_purple_defaults_to_cloud_for_benign_prompt(self) -> None:
        routed = _model_with(_registry(_FULL_ONLINE))
        routed.set_agent("critic")
        d = routed._decide("请总结本轮红蓝对抗的一致性结论")
        assert d["tier"] == "cloud"
        assert d["privacy"] != "local"

    def test_ip_prompt_masked_then_stays_cloud(self) -> None:
        """紫队 prompt 含 IP → 可脱敏 → 允许上云兜底（不被钉死端侧）。"""
        routed = _model_with(_registry(_FULL_ONLINE))
        routed.set_agent("critic")
        d = routed._decide("审查 asset 10.0.0.5 上的攻击链是否成立")
        assert d.get("masked") is True
        assert d["privacy"] != "local"
        assert d["tier"] == "cloud"
        assert "已脱敏" in d["reason"]

    def test_cve_prompt_masked_then_stays_cloud(self) -> None:
        routed = _model_with(_registry(_FULL_ONLINE))
        routed.set_agent("reviewer")
        d = routed._decide("verify chain step T1190 (CVE-2023-32173) on asset-001")
        assert d.get("masked") is True
        assert d["tier"] == "cloud"

    def test_unmaskable_secret_forces_local(self) -> None:
        """脱敏后仍命中（裸"密码"字样）→ 强制 local，禁止落云。"""
        routed = _model_with(_registry(_FULL_ONLINE))
        routed.set_agent("critic")
        d = routed._decide("评审用户表导出内容，其中提到密码策略与病历数据")
        assert d["privacy"] == "local"
        assert d["tier"] in ("device", "edge")
        assert "脱敏后仍敏感" in d["reason"]

    def test_red_agent_stays_device_regardless(self) -> None:
        """红队超低延迟预算 → 始终端侧（延迟因子优先，隐私不改变结果）。"""
        routed = _model_with(_registry(_FULL_ONLINE))
        routed.set_agent("recon")
        d = routed._decide("Scan target range 10.0.0.0/24")
        assert d["tier"] == "device"


class TestHealthAwareSelection:
    def test_avoid_unhealthy_cloud(self) -> None:
        nodes = [dict(n) for n in _FULL_ONLINE]
        for n in nodes:
            if n["tier"] == "cloud":
                n["consecutive_failures"] = 3
        routed = _model_with(_registry(nodes))
        routed.set_agent("critic")
        d = routed._decide("总结对抗结论，评估防御覆盖")
        assert d["tier"] == "edge"
        assert d.get("unhealthy_avoided") == "cloud"
        assert "避让" in d["reason"]

    def test_pick_healthiest_node_in_tier(self) -> None:
        nodes = [dict(n) for n in _FULL_ONLINE]
        nodes.append(
            {"node_id": "edge_server_02", "tier": "edge", "status": "online",
             "model_id": "m", "consecutive_failures": 0, "base_url": "https://x/api"}
        )
        nodes[1]["consecutive_failures"] = 1  # edge_server_01 抖动
        routed = _model_with(_registry(nodes))
        routed.set_agent("detector")
        d = routed._decide("检测事件流中的告警")
        assert d["tier"] == "edge"
        assert d["node_id"] == "edge_server_02"


class TestOfflineDowngradeRegression:
    def test_cloud_only_topology(self) -> None:
        """仅云在线时红队也落云（R20 既有降级语义不回归）。"""
        nodes = [n for n in _FULL_ONLINE if n["tier"] == "cloud"]
        routed = _model_with(_registry(nodes))
        routed.set_agent("recon")
        d = routed._decide("Scan target")
        assert d["tier"] == "cloud"

    def test_no_candidates_fallback(self) -> None:
        routed = _model_with(_registry([]))
        routed.set_agent("critic")
        d = routed._decide("anything")
        assert d.get("fallback") is True


class TestPromptTextExtraction:
    def test_extract_from_dict_items(self) -> None:
        text = RoutedSDKModel._prompt_text(
            [{"type": "message", "content": [{"type": "input_text", "text": "hello 10.0.0.1"}]}]
        )
        assert "10.0.0.1" in text

    def test_extract_from_plain_string(self) -> None:
        assert RoutedSDKModel._prompt_text("plain prompt") == "plain prompt"

    def test_extract_tolerates_garbage(self) -> None:
        assert isinstance(RoutedSDKModel._prompt_text(object()), str)
