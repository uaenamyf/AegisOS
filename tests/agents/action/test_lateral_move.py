from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph, GraphNode, NodeKind
from agents.action.lateral_move.agent import LateralMoveAgent
from agents.tools.llms.mock_provider import MockProvider


def test_plan_moves_returns_lateral_steps():
    mock = MockProvider(responses={
        "default": '{"steps": [{"step_id": "l1", "technique": "T1021", "from_asset": "h1", "to_asset": "h2", "success": true}]}'
    })
    agent = LateralMoveAgent(provider=mock)
    chain = AttackChain(chain_id="c1", target="h1", steps=[
        AttackStep(step_id="s1", technique="T1110", from_asset="ext", to_asset="h1")
    ])
    topo = Graph()
    topo.add_node(GraphNode(node_id="h1", kind=NodeKind.Agent, name="host1"))
    topo.add_node(GraphNode(node_id="h2", kind=NodeKind.Agent, name="host2"))
    steps = agent.plan_moves(chain, topo)
    assert len(steps) == 1
    assert steps[0].technique == "T1021"
    assert steps[0].to_asset == "h2"
