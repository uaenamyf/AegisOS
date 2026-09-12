"""R2 路由桥接集成测试 —— 档案→调度器四规则→端边降级全链路验证。

验证目标（用户要求"端边侧路由也要完善"）：
    NodeProfile(档案) → select_nodes(在线过滤) → to_scheduler_model(候选桥接)
    → schedule()(D1 四规则) 命中的 tier 与预期一致，含逐级降级与能力过滤。
"""

from __future__ import annotations

import pytest

from aegisos_agents.planning.engine.scheduler.scheduler import schedule
from infrastructure.nodes.descriptor import NodeProfile, Tier, select_nodes
from protocol.scheduler import Task


def _profiles() -> list[NodeProfile]:
    return [
        NodeProfile(
            node_id="device_local",
            tier=Tier.DEVICE,
            base_url="http://localhost:11434",
            model_id="tiny",
            capabilities=["chat"],
        ),
        NodeProfile(
            node_id="edge_01",
            tier=Tier.EDGE,
            base_url="http://10.0.0.2:8900",
            model_id="medium",
            capabilities=["chat", "reasoning"],
        ),
        NodeProfile(
            node_id="cloud_api",
            tier=Tier.CLOUD,
            base_url="https://api.example.com",
            provider="openai_api",
            model_id="large",
            capabilities=["chat", "reasoning", "long_context"],
        ),
    ]


def _candidates(nodes: list[NodeProfile]):
    """模拟 R6 派发器的候选构建：在线(enabled)节点 → scheduler.Model。"""
    return [n.to_scheduler_model() for n in select_nodes(nodes)]


# ---------- 端边云三层齐备 ----------


def test_privacy_task_routes_to_device():
    models = _candidates(_profiles())
    m = schedule(Task(goal="解析本机日志", privacy="local"), models)
    assert m.tier == "device"


def test_ultra_low_latency_routes_to_device():
    models = _candidates(_profiles())
    m = schedule(Task(goal="实时告警研判", latency_budget=0.5), models)
    assert m.tier == "device"


def test_low_latency_routes_to_edge():
    models = _candidates(_profiles())
    m = schedule(Task(goal="区域聚合摘要", latency_budget=3.0), models)
    assert m.tier == "edge"


def test_heavy_task_routes_to_cloud():
    models = _candidates(_profiles())
    m = schedule(Task(goal="全域投研报告", latency_budget=60.0), models)
    assert m.tier == "cloud"


# ---------- 端侧离线：端边降级 ----------


def test_device_offline_privacy_degrades_to_edge():
    nodes = [n for n in _profiles() if n.node_id != "device_local"]
    m = schedule(Task(goal="敏感任务但端侧失联", privacy="local"), _candidates(nodes))
    assert m.tier == "edge"


def test_device_offline_low_latency_degrades_to_edge():
    nodes = [n for n in _profiles() if n.node_id != "device_local"]
    m = schedule(Task(goal="实时任务", latency_budget=0.5), _candidates(nodes))
    assert m.tier == "edge"


def test_edge_offline_low_latency_falls_to_device():
    nodes = [n for n in _profiles() if n.node_id != "edge_01"]
    m = schedule(Task(goal="低延迟", latency_budget=3.0), _candidates(nodes))
    assert m.tier == "device"


# ---------- 边云双缺 / 全灭 ----------


def test_only_cloud_left_takes_everything():
    nodes = [n for n in _profiles() if n.tier == Tier.CLOUD]
    for budget in (0.5, 3.0, 60.0):
        m = schedule(Task(goal="x", latency_budget=budget), _candidates(nodes))
        assert m.tier == "cloud"


def test_no_online_node_raises():
    with pytest.raises(ValueError):
        schedule(Task(goal="x"), [])


# ---------- 能力过滤参与路由 ----------


def test_capability_filter_bypasses_device_for_reasoning():
    """端侧只会 chat；要求 reasoning 的低延迟任务应跳过端侧选边侧。"""
    models = _candidates(_profiles())
    m = schedule(
        Task(goal="漏洞关联推理", latency_budget=0.5),
        models,
        required_capability="reasoning",
    )
    assert m.tier == "edge"


def test_disabled_profile_excluded_from_routing():
    nodes = _profiles()
    nodes[2] = nodes[2].model_copy(update={"enabled": False})
    m = schedule(Task(goal="重活", latency_budget=60.0), _candidates(nodes))
    assert m.tier == "edge"
