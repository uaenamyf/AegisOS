"""拓扑图协议类型。

定义 Agent 拓扑图的节点、边、路径与变更差集类型，用于描述
AegisOS 中智能体之间的协作关系与能力分布，支撑任务路由决策。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NodeKind(str, Enum):
    """拓扑节点类型枚举。

    区分拓扑图中不同类型的节点，用于路由与能力匹配。
    """

    Agent = "agent"   # 智能体节点
    Task = "task"      # 任务节点
    Memory = "memory"  # 记忆系统节点
    Tool = "tool"      # 工具节点


@dataclass
class GraphNode:
    """拓扑图节点。

    描述一个智能体或资源的属性，包括能力、信任度与运行指标。

    Attributes:
        node_id: 节点唯一标识。
        kind: 节点类型，参见 NodeKind。
        name: 节点可读名称。
        capabilities: 节点能力列表，用于任务匹配。
        trust_score: 信任分数，0.0-1.0。
        success_rate: 历史成功率，0.0-1.0。
        latency: 平均响应延迟（秒）。
        status: 节点状态：active / idle / degraded。
    """

    node_id: str
    kind: NodeKind
    name: str = ""
    capabilities: list = field(default_factory=list)
    trust_score: float = 1.0
    success_rate: float = 1.0
    latency: float = 0.0
    status: str = "active"  # active | idle | degraded


@dataclass
class GraphEdge:
    """拓扑图边。

    描述两个节点之间的协作关系，包含权重、熵与延迟等路由指标。

    Attributes:
        src: 源节点 ID。
        dst: 目标节点 ID。
        weight: 边权重，影响路由优先级。
        entropy: 路由熵，衡量不确定性。
        latency: 该边的平均延迟（秒）。
        trust_score: 该协作关系的信任分数。
        success_rate: 该协作关系的历史成功率。
    """

    src: str
    dst: str
    weight: float = 1.0
    entropy: float = 0.0
    latency: float = 0.0
    trust_score: float = 1.0
    success_rate: float = 1.0


@dataclass
class Graph:
    """拓扑图。

    维护节点与边的集合，提供基础的增删操作。

    Attributes:
        nodes: 节点字典，key 为 node_id，value 为 GraphNode。
        edges: 边列表。
    """

    nodes: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)

    def add_node(self, n: GraphNode) -> None:
        """向拓扑图添加节点。

        若 node_id 已存在则会覆盖原节点。

        Args:
            n: 要添加的 GraphNode。
        """
        self.nodes[n.node_id] = n

    def add_edge(self, e: GraphEdge) -> None:
        """向拓扑图添加边。

        Args:
            e: 要添加的 GraphEdge。
        """
        self.edges.append(e)


@dataclass
class Route:
    """路由路径。

    描述一次任务路由选择的路径及其代价指标。

    Attributes:
        task_id: 关联的任务 ID。
        path: 节点 ID 有序列表，表示路径经过的节点。
        cost: 路径总代价。
        entropy: 路径总熵。
    """

    task_id: str
    path: list = field(default_factory=list)
    cost: float = 0.0
    entropy: float = 0.0


@dataclass
class GraphDiff:
    """拓扑图变更差集。

    描述两次拓扑快照之间的增量变化，用于同步拓扑更新。

    Attributes:
        added_nodes: 新增的 GraphNode 列表。
        removed_nodes: 移除的节点 ID 列表。
        added_edges: 新增的 GraphEdge 列表。
        removed_edges: 移除的边列表。
        updated_edges: 属性发生变更的 GraphEdge 列表。
    """

    added_nodes: list = field(default_factory=list)
    removed_nodes: list = field(default_factory=list)
    added_edges: list = field(default_factory=list)
    removed_edges: list = field(default_factory=list)
    updated_edges: list = field(default_factory=list)
