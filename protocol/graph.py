from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NodeKind(str, Enum):
    Agent = "agent"
    Task = "task"
    Memory = "memory"
    Tool = "tool"


@dataclass
class GraphNode:
    node_id: str
    kind: NodeKind
    name: str = ""
    capabilities: list = field(default_factory=list)
    trust_score: float = 1.0
    success_rate: float = 1.0
    latency: float = 0.0


@dataclass
class GraphEdge:
    src: str
    dst: str
    weight: float = 1.0
    entropy: float = 0.0
    latency: float = 0.0
    trust_score: float = 1.0
    success_rate: float = 1.0


@dataclass
class Graph:
    nodes: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)

    def add_node(self, n: GraphNode) -> None:
        self.nodes[n.node_id] = n

    def add_edge(self, e: GraphEdge) -> None:
        self.edges.append(e)


@dataclass
class Route:
    task_id: str
    path: list = field(default_factory=list)
    cost: float = 0.0
    entropy: float = 0.0


@dataclass
class GraphDiff:
    added_nodes: list = field(default_factory=list)
    removed_nodes: list = field(default_factory=list)
    added_edges: list = field(default_factory=list)
    removed_edges: list = field(default_factory=list)
    updated_edges: list = field(default_factory=list)
