# @aegis-gen
# date: 2026-06-27
# dev: Claude Code (glm-5.2)
# change: 新建 GraphService（实现 backend.api.GraphAPI，订阅 graph.update 维护图缓存）
from __future__ import annotations

import contextlib

from agents.api import EventBusAPI
from protocol import Event, Graph


class GraphService:
    """Implements ``backend.api.GraphAPI`` with an in-memory graph cache.

    The cache is refreshed via ``EventBusAPI.subscribe("graph.update", ...)``.
    Until agents P5 emits real graph diffs, an empty ``Graph`` is returned.
    """

    def __init__(self, event_bus: EventBusAPI) -> None:
        self._event_bus = event_bus
        self._graph = Graph()
        with contextlib.suppress(Exception):
            self._event_bus.subscribe("graph.update", self._on_graph_update)

    def _on_graph_update(self, event: Event) -> None:
        # Placeholder: apply GraphDiff payload to the cached graph once agents emit it.
        payload = event.payload or {}
        for node in payload.get("added_nodes", []):
            self._graph.add_node(node)
        for edge in payload.get("added_edges", []):
            self._graph.add_edge(edge)

    async def get_graph(self) -> Graph:
        return self._graph
