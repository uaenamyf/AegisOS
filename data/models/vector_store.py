# date: 2026-08-06
# dev: czy
"""向量存储实现 —— InMemory + Qdrant 双实现适配层。

提供 :class:`InMemoryVectorStore`（默认，纯内存余弦检索）与
:class:`QdrantVectorStore`（真实 Qdrant 客户端，惰性加载）。
两实现均满足 ``data.api.VectorStoreAPI`` 语义：add/search/delete/count/all。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    payload: dict[str, Any] = field(default_factory=dict)


class InMemoryVectorStore:
    """内存向量存储 —— 默认零依赖实现。

    Attributes:
        _items: 已索引向量列表（保持写入顺序，同分检索稳定）。
    """

    def __init__(self) -> None:
        """初始化空的内存向量存储。"""
        self._items: list[_VectorItem] = []

    def add(
        self, vector_id: str, vector: list[float], payload: dict[str, Any] | None = None
    ) -> None:
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

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict[str, Any], float]]:
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

    def all(self) -> list[tuple[str, dict[str, Any]]]:
        """返回全部 ``(vector_id, payload)``（按写入顺序）。"""
        return [(it.vector_id, it.payload) for it in self._items]


# date: 2026-08-06
# dev: czy
# changelog: 新增 QdrantVectorStore —— 真实 Qdrant 客户端适配器（H2，惰性加载）
class QdrantVectorStore:
    """Qdrant 向量存储 —— 真实客户端适配器（惰性加载）。

    首次方法调用时 ``import qdrant_client``；未安装或连接失败时抛错，
    不做静默降级（由装配方决定是否回退内存实现）。
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str = "",
        collection: str = "memory_vectors",
        timeout: float = 10.0,
    ) -> None:
        """初始化 Qdrant 客户端参数（不建立连接）。

        Args:
            url: Qdrant 服务地址。
            api_key: 可选 API Key。
            collection: 集合名。
            timeout: 连接超时（秒）。
        """
        self._url = url
        self._api_key = api_key
        self._collection = collection
        self._timeout = timeout
        self._client: Any | None = None  # 惰性：构造不导入三方包

    def _get_client(self) -> Any:
        """惰性获取 Qdrant 客户端（首次调用导入驱动并连接）。

        Raises:
            RuntimeError: 未安装 qdrant-client 时。
            ConnectionError: 连接失败时。
        """
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise RuntimeError("qdrant-client 未安装，请 pip install aegisos[storage]") from exc
        try:
            client = QdrantClient(url=self._url, api_key=self._api_key, timeout=self._timeout)
        except Exception as exc:  # pragma: no cover - 网络路径
            raise ConnectionError(f"无法连接 Qdrant: {exc}") from exc
        self._client = client
        return client

    def add(
        self, vector_id: str, vector: list[float], payload: dict[str, Any] | None = None
    ) -> None:
        """upsert 一条向量到 Qdrant（首次调用创建集合）。

        Args:
            vector_id: 向量唯一标识（Qdrant point id）。
            vector: 向量本体。
            payload: 附加元数据。
        """
        if not vector:
            return
        client = self._get_client()
        try:
            from qdrant_client.http.exceptions import UnexpectedResponse  # noqa: PLC0415
            from qdrant_client.models import Distance, PointStruct, VectorParams  # noqa: PLC0415

            try:
                client.get_collection(self._collection)
            except (UnexpectedResponse, ValueError):
                client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE),
                )
            client.upsert(
                collection_name=self._collection,
                points=[PointStruct(id=vector_id, vector=vector, payload=payload or {})],
            )
        except Exception as exc:  # pragma: no cover - 网络路径
            raise ConnectionError(f"Qdrant upsert 失败: {exc}") from exc

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict[str, Any], float]]:
        """按查询向量检索 Top-K（返回 id/payload/score）。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限。
        """
        if not query:
            return []
        client = self._get_client()
        hits = client.search(
            collection_name=self._collection,
            query_vector=query,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [(str(h.id), dict(h.payload or {}), float(h.score)) for h in hits]

    def delete(self, vector_id: str) -> None:
        """删除指定向量（不存在则静默）。"""
        client = self._get_client()
        client.delete(collection_name=self._collection, points_selector=[vector_id])

    def count(self) -> int:
        """返回集合内向量条数。"""
        client = self._get_client()
        info = client.count(collection_name=self._collection, exact=True)
        return int(info.count or 0)

    def all(self) -> list[tuple[str, dict[str, Any]]]:
        """滚动返回全部 ``(id, payload)``（演示规模足够，取前 1000 条）。"""
        client = self._get_client()
        points, _ = client.scroll(
            collection_name=self._collection, limit=1000, with_payload=True, with_vectors=False
        )
        return [(str(p.id), dict(p.payload or {})) for p in points]
