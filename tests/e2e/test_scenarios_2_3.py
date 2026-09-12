# date: 2026-09-01
# dev: ox-alpha
"""场景 2/3 Mock 端到端验收：长程攻击链与端边云协同。"""

from __future__ import annotations

from aegisos_agents.action.exploit_planner.agent import ExploitPlannerAgent
from aegisos_agents.action.lateral_move.agent import LateralMoveAgent
from aegisos_agents.action.recon.agent import ReconAgent
from backend.mocks.cyber_provider import _CyberMockProvider
from data.models.graph_store import InMemoryGraphStore
from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, Tier
from infrastructure.nodes.dispatcher import ExecutionDispatcher
from infrastructure.nodes.registry import NodeRegistry
from protocol.cyber import Asset, AttackChain, VulnFinding
from protocol.graph import Graph, GraphNode, NodeKind
from protocol.scheduler import Task


class _FakeNode:
    def __init__(self, profile: NodeProfile, *, infer_ok: bool = True) -> None:
        self.profile = profile
        self.infer_ok = infer_ok

    def health(self, timeout_s: float = 3.0) -> bool:
        return self.infer_ok

    def infer(self, prompt: str, *, system: str = "", **kwargs: object) -> InferenceResult:
        if not self.infer_ok:
            return InferenceResult.failure(error="edge unavailable")
        return InferenceResult(
            ok=True,
            text=f"{self.profile.node_id}: {prompt}",
            node_id=self.profile.node_id,
            tier=str(self.profile.tier),
            model_id=self.profile.model_id,
        )


def test_scenario2_long_range_chain_reaches_lateral_movement() -> None:
    """红队链路应从发现漏洞推进到至少一个横向移动步骤。"""
    provider = _CyberMockProvider()
    assets = ReconAgent(provider).scan("10.0.0.0/24")
    findings = [
        VulnFinding(
            finding_id="v-1",
            cve_id="CVE-2019-0708",
            asset_id=assets[0].asset_id,
            cvss=9.8,
            attack_surface="rdp",
        )
    ]
    chain = ExploitPlannerAgent(provider).plan(findings)
    topology = Graph(
        nodes={
            asset.asset_id: GraphNode(
                node_id=asset.asset_id,
                kind=NodeKind.Agent,
                name=asset.host,
            )
            for asset in assets
        }
    )
    lateral_steps = LateralMoveAgent(provider).plan_moves(chain, topology)
    long_chain = AttackChain(
        chain_id=chain.chain_id,
        target=chain.target,
        steps=chain.steps + lateral_steps,
        status=chain.status,
    )

    assert isinstance(long_chain, AttackChain)
    assert len(long_chain.steps) >= 2
    assert any(step.from_asset and step.to_asset for step in long_chain.steps)


def test_scenario3_private_task_degrades_from_device_to_edge_and_persists_topology() -> None:
    """端侧不可用时，敏感任务应按降级链进入边侧，拓扑仍可持久化。"""
    profiles = [
        NodeProfile(node_id="device", tier=Tier.DEVICE, model_id="tiny"),
        NodeProfile(node_id="edge", tier=Tier.EDGE, model_id="medium"),
    ]
    device = _FakeNode(profiles[0], infer_ok=False)
    edge = _FakeNode(profiles[1])
    registry = NodeRegistry()
    registry.register_node(device)
    registry.register_node(edge)
    registry.tick()
    dispatcher = ExecutionDispatcher(registry)
    result = dispatcher.dispatch(Task(goal="分析敏感日志", privacy="local"), "secret log")

    graph_store = InMemoryGraphStore(seed_attck=False)
    graph_store.save_topology(
        "scenario-3",
        [
            Asset(asset_id="device", host="10.0.0.10", os="Linux"),
            Asset(asset_id="edge", host="10.0.0.20", os="Linux"),
        ],
        [("device", "internal", "edge")],
    )

    assets, links = graph_store.get_topology("scenario-3")
    assert result.ok is True
    assert result.tier == "edge"
    assert result.privacy_note
    assert len(assets) == 2
    assert links == [("device", "internal", "edge")]
