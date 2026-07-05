# date: 2026-07-06
# dev: myf
# changelog: 实现向量记忆存储（内存余弦相似度检索，Qdrant 接入预留位）
"""向量记忆存储模块。

向量记忆为记忆系统提供"语义相似度"召回通道：每条 ``MemoryPacket`` 携带
``embedding``（list[float]）向量，``search`` 据查询向量做余弦相似度排序返回 Top-K。
当前为纯内存实现，是 Qdrant 向量库接入（H2）的预留位 —— 接口保持稳定，
后续可无缝替换底层为 Qdrant client。

设计要点：
    - 仅索引 ``embedding`` 非空的记忆；空向量不参与相似度计算。
    - 余弦相似度 = dot(a,b) / (|a|*|b|)；查询向量为空时返回空列表。
    - Top-K 截断，避免上下文过长；同分按写入顺序保持稳定。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


def _cosine(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    Args:
        a: 向量 A。
        b: 向量 B（维度需与 A 一致，否则按较短的逐元素相乘）。

    Returns:
        相似度值域 [-1, 1]；任一向量范数为 0 时返回 0.0（避免除零）。
    """
    # 逐元素点积；维度不一致时取较短长度，保证不越界
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    # 显式 float() 标注，避免 sum() 在 strict 模式下推断为 Any
    dot = float(sum(a[i] * b[i] for i in range(n)))
    norm_a = float(sum(x * x for x in a)) ** 0.5
    norm_b = float(sum(x * x for x in b)) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0  # 零向量无方向，相似度定义为 0
    return float(dot / (norm_a * norm_b))


class VectorMemory:
    """向量记忆存储 —— 基于余弦相似度的语义检索（Qdrant 预留位）。

    以 ``list[MemoryPacket]`` 维护带 embedding 的记忆，``search`` 据查询向量
    按相似度降序返回 Top-K。未来可替换底层为 Qdrant，对外接口不变。

    Attributes:
        _items: 已索引的记忆列表（仅含 embedding 非空者）。
    """

    def __init__(self) -> None:
        """初始化空的向量记忆存储。"""
        self._items: list[MemoryPacket] = []

    def add(self, packet: MemoryPacket) -> None:
        """索引一条记忆向量。

        仅当 ``packet.embedding`` 非空时才加入索引；空向量无法参与相似度计算。

        Args:
            packet: 待索引的记忆片段，须携带 ``embedding``。
        """
        if packet.embedding:  # 空列表跳过，避免无效索引项
            self._items.append(packet)

    def search(self, query: list[float], top_k: int = 5) -> list[MemoryPacket]:
        """按查询向量做余弦相似度检索，返回 Top-K 记忆。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限，默认 5。

        Returns:
            按相似度降序排列的记忆列表，长度不超过 ``top_k``。
        """
        if not query or not self._items or top_k <= 0:
            return []
        scored = [(p, _cosine(query, p.embedding)) for p in self._items]
        # 按相似度降序；同分保持原写入顺序（stable sort）
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in scored[:top_k]]

    def all(self) -> list[MemoryPacket]:
        """返回全部已索引的记忆（按写入顺序）。"""
        return list(self._items)

    def __len__(self) -> int:
        """返回已索引的记忆条数。"""
        return len(self._items)
