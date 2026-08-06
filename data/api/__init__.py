# date: 2026-08-06
# dev: czy
"""Data domain public API.

其他模块只从 ``data.api`` 导入；禁止 import ``data.models`` / ``data.datasets`` 内部实现。
"""

from __future__ import annotations

from typing import Any, Protocol

from protocol.cyber import Asset
from protocol.memory import MemoryPacket


class DatasetAPI(Protocol):
    def load(self, name: str, version: str = "latest") -> Any: ...
    def list_datasets(self) -> list: ...
    def preprocess(self, name: str, config: dict) -> Any: ...


class ModelSchemaAPI(Protocol):
    def register_schema(self, name: str, schema: dict) -> None: ...
    def validate(self, name: str, data: dict) -> bool: ...
    def get_schema(self, name: str) -> dict: ...
    def migrate(self, name: str, from_ver: str, to_ver: str) -> Any: ...


class VectorStoreAPI(Protocol):
    """向量存储接口 —— 记忆嵌入向量的增删查（Qdrant / 内存双实现）。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    def add(self, vector_id: str, vector: list[float], payload: dict | None = None) -> None:
        """写入/覆盖一条向量（幂等）。

        Args:
            vector_id: 向量唯一标识。
            vector: 向量本体；为空时跳过。
            payload: 附加元数据（如 MemoryPacket 序列化字段）。
        """
        ...

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, dict, float]]:
        """按查询向量检索 Top-K。

        Args:
            query: 查询向量；为空时返回空列表。
            top_k: 返回条数上限。

        Returns:
            ``[(vector_id, payload, score)]`` 按相似度降序。
        """
        ...

    def delete(self, vector_id: str) -> None:
        """删除指定向量（不存在则静默）。"""
        ...

    def count(self) -> int:
        """返回已索引向量条数。"""
        ...

    def all(self) -> list[tuple[str, dict]]:
        """返回全部 ``(vector_id, payload)``。"""
        ...


class GraphStoreAPI(Protocol):
    """图存储接口 —— 网络拓扑 + ATT&CK 知识（Neo4j / 内存双实现）。

    Attributes:
        无实例属性；本接口为 ``Protocol``，仅约束方法签名。
    """

    # ---- 网络拓扑 ----
    def save_topology(self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]) -> None:
        """保存一个拓扑（按 scope 归组，覆盖写）。

        Args:
            scope: 拓扑作用域标识。
            assets: 资产节点列表。
            links: (src, rel, dst) 关系列表。
        """
        ...

    def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]:
        """读取指定作用域拓扑。

        Returns:
            ``(assets, links)``；不存在时 ``([], [])``。
        """
        ...

    def list_topologies(self) -> list[str]:
        """返回全部已保存的拓扑作用域。"""
        ...

    # ---- ATT&CK 知识 ----
    def seed_attck(self, entries: list[MemoryPacket]) -> int:
        """批量写入 ATT&CK 技战术条目。

        Returns:
            写入条数。
        """
        ...

    def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None:
        """按 ID 单条写入/覆盖一条技战术。"""
        ...

    def get_technique(self, technique_id: str) -> MemoryPacket | None:
        """按 ID 查询技战术；未找到返回 None。"""
        ...

    def search_techniques(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索技战术。"""
        ...

    def all_techniques(self) -> list[MemoryPacket]:
        """返回全部技战术。"""
        ...

    def add_relation(self, src: str, rel: str, dst: str) -> None:
        """添加关系边（rel ∈ contains/precedes/uses/targets）。"""
        ...

    def related_techniques(self, technique_id: str, relation: str | None = None) -> list[MemoryPacket]:
        """返回与指定技战术关联的其他技战术（双向）。"""
        ...


def create_graph_store(mode: str = "in_memory", **kwargs) -> GraphStoreAPI:
    """按 mode 创建图存储（``"in_memory"`` 默认 / ``"neo4j"``）。

    Args:
        mode: 存储模式。
        **kwargs: 连接参数。

    Returns:
        满足 :class:`GraphStoreAPI` 的图存储实例。
    """
    from data.models.registry import create_graph_store as _create

    return _create(mode, **kwargs)


def create_vector_store(mode: str = "in_memory", **kwargs) -> VectorStoreAPI:
    """按 mode 创建向量存储（``"in_memory"`` 默认 / ``"qdrant"``）。

    Args:
        mode: 存储模式。
        **kwargs: 连接参数。

    Returns:
        满足 :class:`VectorStoreAPI` 的向量存储实例。
    """
    from data.models.registry import create_vector_store as _create

    return _create(mode, **kwargs)


def load_attck_dataset() -> list[MemoryPacket]:
    """加载 ATT&CK 数据集为 MemoryPacket 列表（记忆子系统预载共用源）。

    Returns:
        技战术知识包列表。
    """
    from data.datasets.attck.knowledge import load_attck_dataset as _load

    return _load()


__all__ = [
    "DatasetAPI",
    "ModelSchemaAPI",
    "GraphStoreAPI",
    "VectorStoreAPI",
    "create_graph_store",
    "create_vector_store",
    "load_attck_dataset",
]
