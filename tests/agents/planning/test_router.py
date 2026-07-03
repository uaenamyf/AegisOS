from protocol.message import Message, NodeRef
from protocol.graph import Graph, GraphNode, NodeKind
from agents.planning.engine.router.router import route, TOP_K


def test_route_is_sparse_not_broadcast():
    g = Graph()
    for i in range(10):
        g.add_node(GraphNode(
            node_id=f"n{i}", kind=NodeKind.Agent,
            capabilities=["recon"], status="active",
        ))
    msg = Message()
    targets = route(msg, g, required_capability="recon")
    assert 0 < len(targets) <= TOP_K
    assert len(targets) < len(g.nodes)
    assert all(isinstance(t, NodeRef) for t in targets)


def test_route_skips_idle_and_wrong_capability():
    g = Graph()
    g.add_node(GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="idle"))
    g.add_node(GraphNode(node_id="b", kind=NodeKind.Agent, capabilities=["hunt"], status="active"))
    assert route(Message(), g, required_capability="recon") == []


def test_route_prefers_higher_success_rate():
    g = Graph()
    g.add_node(GraphNode(node_id="low", kind=NodeKind.Agent, capabilities=["recon"], success_rate=0.3, status="active"))
    g.add_node(GraphNode(node_id="high", kind=NodeKind.Agent, capabilities=["recon"], success_rate=0.9, status="active"))
    targets = route(Message(), g, required_capability="recon")
    assert targets[0].node_id == "high"


def test_route_returns_empty_on_empty_graph():
    g = Graph()
    assert route(Message(), g, required_capability="recon") == []
