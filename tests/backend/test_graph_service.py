# date: 2026-09-01
# dev: ox-alpha
"""GraphService 图更新事件与协议类型转换测试。"""

from __future__ import annotations

import asyncio

from backend.services.graph_service import GraphService
from protocol import Event, EventType, GraphEdge, GraphNode, NodeKind


class _EventBus:
    def subscribe(self, topic: str, handler) -> None:
        self.handler = handler


def test_graph_update_converts_dict_payload_to_protocol_nodes_and_edges() -> None:
    service = GraphService(_EventBus())
    event = Event(
        event_type=EventType.GraphUpdate,
        payload={
            "added_nodes": [
                {"node_id": "agent-a", "kind": "agent", "name": "Recon"}
            ],
            "added_edges": [{"src": "agent-a", "dst": "agent-b", "weight": 0.8}],
        },
    )

    service._on_graph_update(event)
    graph = asyncio.run(service.get_graph())

    assert isinstance(graph.nodes["agent-a"], GraphNode)
    assert graph.nodes["agent-a"].kind == NodeKind.Agent
    assert isinstance(graph.edges[0], GraphEdge)
    assert graph.edges[0].weight == 0.8


def test_graph_update_applies_removals_and_edge_updates() -> None:
    service = GraphService(_EventBus())
    service._on_graph_update(
        Event(
            event_type=EventType.GraphUpdate,
            payload={
                "added_nodes": [
                    {"node_id": "a", "kind": "agent"},
                    {"node_id": "b", "kind": "agent"},
                ],
                "added_edges": [{"src": "a", "dst": "b", "weight": 0.2}],
            },
        )
    )
    service._on_graph_update(
        Event(
            event_type=EventType.GraphUpdate,
            payload={
                "updated_edges": [{"src": "a", "dst": "b", "weight": 0.9}],
                "removed_nodes": ["b"],
            },
        )
    )

    graph = asyncio.run(service.get_graph())
    assert list(graph.nodes) == ["a"]
    assert graph.edges[0].weight == 0.9

    service._on_graph_update(
        Event(
            event_type=EventType.GraphUpdate,
            payload={"removed_edges": [{"src": "a", "dst": "b"}]},
        )
    )
    assert asyncio.run(service.get_graph()).edges == []
