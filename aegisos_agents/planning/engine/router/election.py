# date: 2026-07-04
# dev: myf
# changelog: 异构选举
"""异构选举模块（基于点积相似度）。

在多个同质但异构的执行实例中，依据"任务特征向量"与"节点能力向量"的点积
相似度选出最匹配的实例，实现细粒度的任务-实例匹配。

主要导出：
    - elect: 选举入口，返回得分最高的 NodeRef。
"""
from __future__ import annotations

from protocol.graph import GraphNode
from protocol.message import NodeRef


def elect(
    task_features: list[float],
    instances: list[GraphNode],
    capability_vectors: dict[str, list[float]],
) -> NodeRef:
    """异构选举：选取能力向量与任务特征向量点积最大的实例。

    点积相似度衡量任务需求与节点能力的匹配程度：向量同向（能力契合）时
    得分高，正交（能力无关）时得分趋零。选用点积而非余弦，因能力幅值
    本身代表强度，幅值越大代表该能力越强，应给予更高权重。

    Args:
        task_features: 任务特征向量，各维代表对某项能力的需求强度。
        instances: 参与选举的候选节点列表。
        capability_vectors: 节点 ID 到其能力向量的映射。

    Returns:
        得分最高实例的 NodeRef；无候选时返回空 NodeRef。
    """
    # 无候选实例：返回空引用，由上游决定降级策略
    if not instances:
        return NodeRef(node_id="", node_type="agent")

    best_node = None
    best_score = float("-inf")  # 初始负无穷，保证首个实例必被选中

    for inst in instances:
        # 取该节点的能力向量；缺失时视为空向量，点积为 0
        vec = capability_vectors.get(inst.node_id, [])
        # 点积 = Σ(任务特征 × 能力幅值)；逐维相乘后求和
        score = sum(f * v for f, v in zip(task_features, vec))
        if score > best_score:
            best_score = score
            best_node = inst

    return NodeRef(
        node_id=best_node.node_id,
        node_type=best_node.kind.value,
    )
