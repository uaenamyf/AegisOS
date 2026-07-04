# @aegis-gen
# date: 2026-06-27
# dev: myf
# change: 新建 GraphService（实现 backend.api.GraphAPI，订阅 graph.update 维护图缓存）
"""Graph 服务层：维护内存中的图缓存，并订阅事件总线刷新缓存。"""

from __future__ import annotations

import contextlib

from agents.api import EventBusAPI
from protocol import Event, Graph


class GraphService:
    """实现 ``backend.src.api.GraphAPI``，在内存中维护图缓存。

    缓存通过 ``EventBusAPI.subscribe("graph.update", ...)`` 订阅事件刷新。
    在 agents P5 阶段发出真实图差异之前，返回空的 ``Graph``。

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
        # 占位实现：待 agents 发出真实图差异后，将其应用到缓存图。
        payload = event.payload or {}
        for node in payload.get("added_nodes", []):  # 新增节点
            self._graph.add_node(node)
        for edge in payload.get("added_edges", []):  # 新增边
            self._graph.add_edge(edge)

    async def get_graph(self) -> Graph:
        """获取当前的图缓存。

        Returns:
            内存中缓存的 ``Graph`` 对象。
        """
        return self._graph
