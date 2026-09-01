# date: 2026-06-27
# dev: myf
"""Graph 服务层：维护内存中的图缓存，并订阅事件总线刷新缓存。"""

from __future__ import annotations

import contextlib

from aegisos_agents.api import EventBusAPI
from protocol import Event, Graph, GraphEdge, GraphNode


class GraphService:
    """实现 ``backend.api.GraphAPI``，在内存中维护图缓存。

    缓存通过 ``EventBusAPI.subscribe("graph.update", ...)`` 订阅事件刷新，
    将事件负载转换为协议层节点和边后应用增量变更。

    Attributes:
        _event_bus: 事件总线 API，用于订阅 graph.update 事件。
        _graph: 内存中的图缓存对象。
    """

    def __init__(self, event_bus: EventBusAPI) -> None:
        self._event_bus = event_bus
        self._graph = Graph()  # 初始化空图缓存
        # 订阅 graph.update 事件，异常时静默忽略（事件总线可能尚未就绪）
        with contextlib.suppress(Exception):
            self._event_bus.subscribe("graph.update", self._on_graph_update)

    def _on_graph_update(self, event: Event) -> None:
        """graph.update 事件的回调处理器。

        将事件 payload 中的节点和边增量应用到缓存图上。

        Args:
            event: 携带 GraphDiff payload 的事件对象。
        """
        payload = event.payload or {}
        for node in payload.get("added_nodes", []):
            graph_node = node if isinstance(node, GraphNode) else GraphNode.model_validate(node)
            self._graph.add_node(graph_node)

        for node_id in payload.get("removed_nodes", []):
            self._graph.nodes.pop(str(node_id), None)

        for edge in payload.get("removed_edges", []):
            removed = edge if isinstance(edge, GraphEdge) else GraphEdge.model_validate(edge)
            self._graph.edges = [
                current
                for current in self._graph.edges
                if not (current.src == removed.src and current.dst == removed.dst)
            ]

        for edge in payload.get("updated_edges", []):
            updated = edge if isinstance(edge, GraphEdge) else GraphEdge.model_validate(edge)
            self._graph.edges = [
                updated if current.src == updated.src and current.dst == updated.dst else current
                for current in self._graph.edges
            ]

        for edge in payload.get("added_edges", []):
            graph_edge = edge if isinstance(edge, GraphEdge) else GraphEdge.model_validate(edge)
            self._graph.add_edge(graph_edge)

    async def get_graph(self) -> Graph:
        """获取当前的图缓存。

        Returns:
            内存中缓存的 ``Graph`` 对象。
        """
        return self._graph
