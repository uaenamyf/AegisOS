from protocol.graph import Graph, GraphNode, NodeKind
from agents.planning.engine.topology.topology import active_subgraph


def test_active_subgraph_filters_capability_and_status():
    a = GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="active")
    b = GraphNode(node_id="b", kind=NodeKind.Agent, capabilities=["recon"], status="idle")
    c = GraphNode(node_id="c", kind=NodeKind.Agent, capabilities=["hunt"], status="active")
    g = Graph()
    for n in (a, b, c):
        g.add_node(n)
    sub = active_subgraph(g, required_capability="recon")
    assert list(sub.nodes.keys()) == ["a"]


def test_active_subgraph_includes_degraded_if_explicit():
    a = GraphNode(node_id="a", kind=NodeKind.Agent, capabilities=["recon"], status="active")
    d = GraphNode(node_id="d", kind=NodeKind.Agent, capabilities=["recon"], status="degraded")
    g = Graph()
    g.add_node(a)
    g.add_node(d)
    sub = active_subgraph(g, required_capability="recon")
    assert set(sub.nodes.keys()) == {"a", "d"}


def test_active_subgraph_empty_when_no_match():
    g = Graph()
    g.add_node(GraphNode(node_id="x", kind=NodeKind.Agent, capabilities=["hunt"], status="active"))
    sub = active_subgraph(g, required_capability="recon")
    assert len(sub.nodes) == 0
