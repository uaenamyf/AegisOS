# date: 2026-07-04
# dev: myf
# changelog: 低熵稀疏路由 Top-K
"""低熵稀疏路由器（Top-K 稀疏路由）。

本模块实现基于亲和度与负载惩罚的 Top-K 稀疏路由策略：
从活跃子图中选取最多 TOP_K 个最匹配的节点，避免向所有具备能力的节点广播，
从而降低消息分发熵值、控制下游并发压力。

主要导出：
    - route: 对外路由入口，返回排序后的候选 NodeRef 列表。
"""
from __future__ import annotations

from aegisos_agents.planning.engine.topology.topology import active_subgraph
from protocol.graph import Graph
from protocol.message import Message, NodeRef

# 稀疏路由的候选上限：每次最多向 TOP_K 个节点分发，避免广播带来的高熵与高负载
TOP_K = 3


def route(
    message: Message,
    topology: Graph,
    required_capability: str,
) -> list[NodeRef]:
    """低熵稀疏路由：返回最多 TOP_K 个最匹配的 NodeRef，绝不广播给所有可用节点。

    路由流程：
        1. 基于所需能力计算活跃子图（剔除离线节点）。
        2. 对每个候选节点按"亲和度 - 负载惩罚"打分。
        3. 降序排序后截取前 TOP_K 个。

    Args:
        message: 待路由的消息，包含目标能力与上下文。
        topology: 全局节点拓扑图。
        required_capability: 路由所需的节点能力标识。

    Returns:
        按得分降序排列的候选节点引用列表，长度不超过 TOP_K。
    """
    # 仅保留状态正常（active/degraded）且具备所需能力的节点
    sub = active_subgraph(topology, required_capability)
    candidates = list(sub.nodes.values())
    # 排序键 = 亲和度（成功率） - 负载惩罚（延迟）；reverse=True 取高分在前
    scored = sorted(
        candidates,
        key=lambda n: _affinity(message, n) - _load_penalty(n),
        reverse=True,
    )
    # 截取 Top-K，候选不足时取全部
    k = min(TOP_K, len(scored))
    return [NodeRef(node_id=n.node_id, node_type=n.kind.value) for n in scored[:k]]


def _affinity(message: Message, n) -> float:
    """计算消息与节点的亲和度。

    当前以节点历史成功率作为亲和度度量；成功率越高越优先被选中。
    缺省返回 1.0，表示无历史数据时视作中性可用。

    Args:
        message: 待路由消息。
        n: 候选图节点。

    Returns:
        亲和度得分，取值 [0, 1]。
    """
    return getattr(n, "success_rate", 1.0)


def _load_penalty(n) -> float:
    """计算节点的负载惩罚值。

    以节点当前延迟作为惩罚度量；延迟越高越应被降权，避免向过载节点分发。
    缺省返回 0.0，表示无延迟数据时不施加惩罚。

    Args:
        n: 候选图节点。

    Returns:
        负载惩罚值（秒），越大越应被回避。
    """
    return getattr(n, "latency", 0.0)
