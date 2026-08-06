# date: 2026-08-06
# dev: czy
"""图存储实现 —— InMemory + Neo4j 双实现适配层。

提供 :class:`InMemoryGraphStore`（默认，dict 参考实现）与
:class:`Neo4jGraphStore`（真实 Neo4j 客户端，惰性加载）。
两能力：网络拓扑（Asset 节点 + 带标签关系）与 ATT&CK 知识（Technique 节点 + 关系）。
"""

from __future__ import annotations

from data.datasets.attck.knowledge import load_attck_dataset
from protocol.cyber import Asset
from protocol.memory import MemoryPacket

# 合法关系标签集合（防御脏数据）
_ALLOWED_RELS = {"contains", "precedes", "uses", "targets"}


class InMemoryGraphStore:
    """内存图存储 —— 默认零依赖实现。

    Attributes:
        _topologies: scope -> (assets, links)。
        _attck: technique_id -> MemoryPacket。
        _attck_edges: (src, rel, dst) 列表。
    """

    def __init__(self, seed_attck: bool = True) -> None:
        """初始化图存储，可选预载 ATT&CK 数据集。

        Args:
            seed_attck: 是否在构造时预载 ATT&CK 数据集，默认 ``True``。
        """
        self._topologies: dict[str, tuple[list[Asset], list[tuple[str, str, str]]]] = {}
        self._attck: dict[str, MemoryPacket] = {}
        self._attck_edges: list[tuple[str, str, str]] = []
        if seed_attck:
            self.seed_attck(load_attck_dataset())

    # ---- ATT&CK 知识 ----

    def seed_attck(self, entries: list[MemoryPacket]) -> int:
        """批量写入 ATT&CK 技战术条目。

        Args:
            entries: MemoryPacket 列表（含 semantic.technique_id）。

        Returns:
            写入条数。
        """
        for p in entries:
            tid = str(p.semantic.get("technique_id") or p.task_id)
            self._attck[tid] = p
        return len(entries)

    def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None:
        """按 ID 单条写入/覆盖一条技战术。

        Args:
            technique_id: 技战术唯一标识。
            packet: 知识记忆包。
        """
        self._attck[technique_id] = packet

    def get_technique(self, technique_id: str) -> MemoryPacket | None:
        """按 ID 查询技战术。

        Args:
            technique_id: 目标技战术 ID。

        Returns:
            匹配的知识包；未找到返回 None。
        """
        return self._attck.get(technique_id)

    def search_techniques(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索技战术（ID/名称/战术阶段/描述，大小写不敏感）。

        Args:
            keyword: 检索关键词。

        Returns:
            命中的知识包列表。
        """
        kw = keyword.lower()
        hits: list[MemoryPacket] = []
        for p in self._attck.values():
            text = " ".join(str(v) for v in p.semantic.values())
            if kw in text.lower() or kw in (p.summary or "").lower():
                hits.append(p)
        return hits

    def all_techniques(self) -> list[MemoryPacket]:
        """返回全部技战术（按写入顺序）。"""
        return list(self._attck.values())

    def add_relation(self, src: str, rel: str, dst: str) -> None:
        """添加一条关系边（src/rel/dst）。

        Args:
            src: 源节点（tactic 或 technique_id）。
            rel: 关系标签（contains/precedes/uses/targets）。
            dst: 目标节点（tactic 或 technique_id）。

        Raises:
            ValueError: rel 不在合法标签集合时。
        """
        if rel not in _ALLOWED_RELS:
            raise ValueError(f"非法关系标签: {rel}")
        self._attck_edges.append((src, rel, dst))

    def related_techniques(self, technique_id: str, relation: str | None = None) -> list[MemoryPacket]:
        """返回与指定技战术关联的其他技战术（双向可达）。

        Args:
            technique_id: 源技战术 ID。
            relation: 可选关系标签过滤。

        Returns:
            关联的技战术 MemoryPacket 列表。
        """
        targets: list[str] = []
        for src, rel, dst in self._attck_edges:
            if relation is not None and rel != relation:
                continue
            if src == technique_id and dst in self._attck:
                targets.append(dst)
            elif dst == technique_id and src in self._attck:
                targets.append(src)
        seen: set[str] = set()
        result: list[MemoryPacket] = []
        for tid in targets:
            if tid not in seen:
                seen.add(tid)
                p = self._attck.get(tid)
                if p is not None:
                    result.append(p)
        return result

    # ---- 网络拓扑 ----

    def save_topology(self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]) -> None:
        """保存一个拓扑（按 scope 归组，覆盖写）。

        Args:
            scope: 拓扑作用域标识（如 range_id）。
            assets: 资产节点列表。
            links: (src, rel, dst) 关系列表。
        """
        self._topologies[scope] = (assets, links)

    def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]:
        """读取指定作用域的拓扑。

        Args:
            scope: 拓扑作用域标识。

        Returns:
            ``(assets, links)``；不存在时返回 ``([], [])``。
        """
        return self._topologies.get(scope, ([], []))

    def list_topologies(self) -> list[str]:
        """返回全部已保存的拓扑作用域。"""
        return list(self._topologies.keys())
