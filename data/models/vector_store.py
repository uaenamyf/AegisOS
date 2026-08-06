# date: 2026-08-06
# dev: czy
"""向量存储实现 —— InMemory + Qdrant 双实现适配层。

提供 :class:`InMemoryVectorStore`（默认，纯内存余弦检索）与
:class:`QdrantVectorStore`（真实 Qdrant 客户端，惰性加载）。
两实现均满足 ``data.api.VectorStoreAPI`` 语义：add/search/delete/count/all。
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _cosine(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    Args:
        a: 向量 A。
        b: 向量 B。

    Returns:
        值域 [-1, 1]；任一向量范数为 0 时返回 0.0。
    """
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = float(sum(a[i] * b[i] for i in range(n)))
    norm_a = float(sum(x * x for x in a)) ** 0.5
    norm_b = float(sum(x * x for x in b)) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


@dataclass
class _VectorItem:
    """内存向量条目。

    Attributes:
        vector_id: 向量唯一标识。
        vector: 向量本体。
        payload: 附加元数据（如序列化后的 MemoryPacket 字段）。
    """

    vector_id: str
    vector: list[float]
    payload: dict = field(default_factory=dict)


class InMemoryVectorStore:
    """内存向量存储 —— 默认零依赖实现。

    Attributes:
        _items: 已索引向量列表（保持写入顺序，同分检索稳定）。
    """

    def __init__(self) -> None:
        """初始化空的内存向量存储。"""
        self._items: list[_VectorItem] = []

    def add(self, vector_id: str, vector: list[float], payload: dict | None = None) -> None:
        """写入/覆盖一条向量（幂等，按 vector_id）。

        Args:
            vector_id: 向量唯一标识。
            vector: 向量本体；为空时跳过。
            payload: 附加元数据，默认空 dict。
        """
        if not vector:
            return
        # 先移除同 id 旧条目，保证幂等
        self._items = [it for it in self._items if it.vector_id != vector_id]
        self._items.append(_VectorItem(vector_id, vector, payload or {}))

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict, float]]:
        """按查询向量余弦相似度检索 Top-K。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限。

        Returns:
            ``[(vector_id, payload, score)]`` 按相似度降序，同分保写入序。
        """
        if not query or not self._items or top_k <= 0:
            return []
        scored = [(it.vector_id, it.payload, _cosine(query, it.vector)) for it in self._items]
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    def delete(self, vector_id: str) -> None:
        """删除指定向量（不存在则静默）。"""
        self._items = [it for it in self._items if it.vector_id != vector_id]

    def count(self) -> int:
        """返回已索引向量条数。"""
        return len(self._items)

    def all(self) -> list[tuple[str, dict]]:
        """返回全部 ``(vector_id, payload)``（按写入顺序）。"""
        return [(it.vector_id, it.payload) for it in self._items]
