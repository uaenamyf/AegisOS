# date: 2026-08-06
# dev: czy
"""存储后端注册表 —— 按 mode 分发生成图/向量存储。

消费方（memory/backend）只经 ``data.api`` 调用本模块的工厂函数，
不直接 import ``data.models`` 内部实现。
"""

from __future__ import annotations

from data.models.graph_store import InMemoryGraphStore, Neo4jGraphStore
from data.models.vector_store import InMemoryVectorStore, QdrantVectorStore


def create_graph_store(mode: str = "in_memory", **kwargs):
    """按 mode 创建图存储。

    Args:
        mode: ``"in_memory"``（默认）/ ``"neo4j"``。
        **kwargs: 透传给具体实现的连接参数（uri/user/password/seed_attck 等）。

    Returns:
        图存储实例（InMemoryGraphStore 或 Neo4jGraphStore）。

    Raises:
        ValueError: mode 未知时。
    """
    if mode == "in_memory":
        return InMemoryGraphStore(**kwargs)
    if mode == "neo4j":
        return Neo4jGraphStore(**kwargs)
    raise ValueError(f"未知 graph_store mode: {mode}")


def create_vector_store(mode: str = "in_memory", **kwargs):
    """按 mode 创建向量存储。

    Args:
        mode: ``"in_memory"``（默认）/ ``"qdrant"``。
        **kwargs: 透传给具体实现的连接参数（url/api_key/collection/timeout 等）。

    Returns:
        向量存储实例（InMemoryVectorStore 或 QdrantVectorStore）。

    Raises:
        ValueError: mode 未知时。
    """
    if mode == "in_memory":
        return InMemoryVectorStore()
    if mode == "qdrant":
        return QdrantVectorStore(**kwargs)
    raise ValueError(f"未知 vector_store mode: {mode}")
