# date: 2026-08-25
# dev: myf
"""CyberOrchestrator RouterAPI 接入测试（spec 04 §16 / 11 §7 铁律）。

覆盖 P3.2：
    - select_targets 走稀疏路由（Top-K）
    - get_topology 返回 11 个攻防 Agent 节点
    - assert_target_routable 在已知 Agent 上不抛
    - assert_target_routable 在非法 capability 上抛 ValueError
    - 业务域零全广播（执行器走 router，不遍历 dispatch）
"""
from __future__ import annotations

import pytest

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from protocol.graph import Graph
from protocol.message import Message, NodeRef


def test_cyber_orchestrator_implements_router_api():
    """编排器实现 RouterAPI（Protocol 结构性子类型，通过方法签名验证）。

    注：Protocol 默认非 ``@runtime_checkable``，无法 ``isinstance`` 校验，
    改用 ``hasattr`` 双方法签名核对（spec 10 §接口边界）。
    """
    orch = CyberOrchestrator()
    assert hasattr(orch, "select_targets")
    assert hasattr(orch, "get_topology")
    assert callable(orch.select_targets)
    assert callable(orch.get_topology)


def test_select_targets_returns_topk_for_capability():
    """select_targets 按 capability 返回 Top-K（<= 3）NodeRef。"""
    orch = CyberOrchestrator()
    targets = orch.select_targets(Message(), "recon")
    assert 0 < len(targets) <= 3
    assert all(isinstance(t, NodeRef) for t in targets)
    # Top-K 内必须包含实际具备该 capability 的节点
    assert any(t.node_id == "recon" for t in targets)


def test_select_targets_different_capability_yields_different_target():
    """不同 capability 返回不同主目标。"""
    orch = CyberOrchestrator()
    recon = orch.select_targets(Message(), "recon")
    hunt = orch.select_targets(Message(), "threat_hunt")
    assert recon[0].node_id != hunt[0].node_id
    assert recon[0].node_id == "recon"
    assert hunt[0].node_id == "threat_hunt"


def test_select_targets_unknown_capability_returns_empty():
    """未知 capability 返回空（非广播、非错误）。"""
    orch = CyberOrchestrator()
    assert orch.select_targets(Message(), "nonsense_capability") == []


def test_get_topology_contains_eleven_agents():
    """编排器拓扑包含 11 个攻防 Agent（红 4 + 蓝 5 + 紫 2）。"""
    orch = CyberOrchestrator()
    topo = orch.get_topology()
    assert isinstance(topo, Graph)
    assert len(topo.nodes) == 11
    expected = {
        "recon", "vuln_correlator", "exploit_planner", "lateral_move",  # 红
        "detector", "triage", "threat_hunt", "ir_planner", "forensics",  # 蓝
        "critic", "reviewer",  # 紫
    }
    assert set(topo.nodes.keys()) == expected


def test_assert_target_routable_passes_for_known_agent():
    """已知 Agent 走 assert_target_routable 不抛。"""
    orch = CyberOrchestrator()
    # 不抛即通过
    orch.assert_target_routable("recon", "recon")
    orch.assert_target_routable("threat_hunt", "threat_hunt")
    orch.assert_target_routable("critic", "critic")


def test_assert_target_routable_raises_for_unknown_target():
    """目标名不在图内时抛 ValueError（spec 04 §16 守卫）。"""
    orch = CyberOrchestrator()
    with pytest.raises(ValueError, match="not in Top-K"):
        orch.assert_target_routable("recon", "ghost_agent")


def test_red_executor_routes_through_sparse_router(monkeypatch):
    """红队 executor 在执行前调用稀疏路由（守卫）。

    将 recon 节点 success_rate 拉到 0，路由亲和度为 0 会被排序到最后（其它也不存在），
    当只有一个候选且其亲和度低于阈值时不在 Top-K — 改为：将 recon 节点完全摘除
    后断言 executor 走 assert_target_routable 路径。
    """
    from aegisos_agents.perception.reasoning.strategies.goal_mode import GoalNode

    orch = CyberOrchestrator()
    # 篡改 _topology：让 recon 节点的 capability 不匹配 → 路由选不到
    orch._topology.nodes["recon"].capabilities = ["other_capability"]
    executor = orch._create_red_agent_executor("10.0.0.0/24")
    node = GoalNode(goal_id="g1", description="recon", agent_name="recon")
    with pytest.raises(ValueError, match="not in Top-K"):
        executor(node, {})


def test_blue_executor_routes_through_sparse_router():
    """蓝队 executor 在执行前调用稀疏路由（守卫）。"""
    from aegisos_agents.perception.reasoning.strategies.goal_mode import GoalNode

    orch = CyberOrchestrator()
    orch._topology.nodes["detector"].capabilities = ["other_capability"]
    executor = orch._create_blue_agent_executor([])
    node = GoalNode(goal_id="g1", description="detect", agent_name="detector")
    with pytest.raises(ValueError, match="not in Top-K"):
        executor(node, {})
