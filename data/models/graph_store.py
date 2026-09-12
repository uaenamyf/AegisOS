# date: 2026-08-06
# dev: czy
"""图存储实现 —— InMemory + Neo4j 双实现适配层。

提供 :class:`InMemoryGraphStore`（默认，dict 参考实现）与
:class:`Neo4jGraphStore`（真实 Neo4j 客户端，惰性加载）。
两能力：网络拓扑（Asset 节点 + 带标签关系）与 ATT&CK 知识（Technique 节点 + 关系）。
"""

from __future__ import annotations

from typing import Any

from data.datasets.attck.knowledge import ATTACK_RELATIONS, load_attck_dataset
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
            # 一并加载数据集关系边，与 Neo4j 实现的 seed 行为保持一致
            self._attck_edges = list(ATTACK_RELATIONS)

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

    def related_techniques(
        self, technique_id: str, relation: str | None = None
    ) -> list[MemoryPacket]:
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

    def save_topology(
        self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]
    ) -> None:
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


# date: 2026-08-06
# dev: czy
# changelog: 新增 Neo4jGraphStore —— 真实 Neo4j 客户端适配器（H2，惰性加载）
class Neo4jGraphStore:
    """Neo4j 图存储 —— 真实客户端适配器（惰性加载）。

    首次方法调用时 ``import neo4j`` 并连接；未安装或连接失败时抛错，
    不做静默降级。拓扑节点 label ``Asset``、技战术节点 label ``Technique``，
    关系 label 即关系标签；``scope`` 作为节点属性归组。
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "",
        database: str | None = None,
    ) -> None:
        """初始化 Neo4j 连接参数（不建立连接）。

        Args:
            uri: bolt 连接地址。
            user: 用户名。
            password: 密码。
            database: 数据库名，默认取 neo4j 默认库。
        """
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver: Any | None = None  # 惰性：构造不导入三方包

    def _get_driver(self) -> Any:
        """惰性获取 neo4j 驱动。

        Raises:
            RuntimeError: 未安装 neo4j 包时。
            ConnectionError: 连接失败时。
        """
        if self._driver is not None:
            return self._driver
        try:
            from neo4j import GraphDatabase  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise RuntimeError("neo4j 驱动未安装，请 pip install aegisos[storage]") from exc
        try:
            driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            driver.verify_connectivity()
        except Exception as exc:  # pragma: no cover - 网络路径
            raise ConnectionError(f"无法连接 Neo4j: {exc}") from exc
        self._driver = driver
        return driver

    # ---- ATT&CK 知识 ----

    def seed_attck(self, entries: list[MemoryPacket]) -> int:
        """批量写入技战术（MERGE 幂等）与 tactic 关系。

        Args:
            entries: MemoryPacket 列表。

        Returns:
            写入条数。
        """
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            for p in entries:
                tid = str(p.semantic.get("technique_id") or p.task_id)
                session.run(
                    "MERGE (t:Technique {technique_id: $tid}) "
                    "SET t.name=$name, t.tactic=$tactic, t.platform=$platform, t.description=$desc",
                    tid=tid,
                    name=p.semantic.get("name", ""),
                    tactic=p.semantic.get("tactic", ""),
                    platform=p.semantic.get("platform", ""),
                    desc=p.semantic.get("description", ""),
                )
                tac = p.semantic.get("tactic", "")
                if tac:
                    session.run(
                        "MERGE (a:Tactic {name:$tac}) MERGE (a)-[:contains]->(t:Technique {technique_id:$tid})",
                        tac=tac,
                        tid=tid,
                    )
            # 创建数据集关系边（与 InMemory 实现的 seed 行为保持一致）
            for src, rel, dst in ATTACK_RELATIONS:
                session.run(
                    f"MATCH (a) WHERE a.technique_id=$src OR a.name=$src "
                    f"MATCH (b) WHERE b.technique_id=$dst OR b.name=$dst "
                    f"MERGE (a)-[:{rel}]->(b)",
                    src=src,
                    dst=dst,
                )
        return len(entries)

    def upsert_technique(self, technique_id: str, packet: MemoryPacket) -> None:
        """按 ID 幂等写入一条技战术（MERGE）。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run(
                "MERGE (t:Technique {technique_id: $tid}) "
                "SET t.name=$name, t.tactic=$tactic, t.platform=$platform, t.description=$desc",
                tid=technique_id,
                name=packet.semantic.get("name", ""),
                tactic=packet.semantic.get("tactic", ""),
                platform=packet.semantic.get("platform", ""),
                desc=packet.semantic.get("description", ""),
            )

    def get_technique(self, technique_id: str) -> MemoryPacket | None:
        """按 ID 查询技战术，还原为 MemoryPacket。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            rec = session.run(
                "MATCH (t:Technique {technique_id: $tid}) RETURN t", tid=technique_id
            ).single()
        if rec is None:
            return None
        props = rec["t"]
        return MemoryPacket(
            task_id=technique_id,
            summary=f"{technique_id} {props.get('name', '')}",
            semantic={
                "technique_id": technique_id,
                "name": props.get("name", ""),
                "tactic": props.get("tactic", ""),
                "platform": props.get("platform", ""),
                "description": props.get("description", ""),
            },
            kind="decision",
        )

    def search_techniques(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索技战术（名称/战术/ID 模糊匹配）。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run(
                "MATCH (t:Technique) WHERE toLower(t.technique_id) CONTAINS $kw "
                "OR toLower(t.name) CONTAINS $kw OR toLower(t.tactic) CONTAINS $kw "
                "RETURN t.technique_id AS tid ORDER BY tid",
                kw=keyword.lower(),
            ).data()
        return [self._get_technique_or_blank(r["tid"]) for r in recs]

    def all_techniques(self) -> list[MemoryPacket]:
        """返回全部技战术。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run(
                "MATCH (t:Technique) RETURN t.technique_id AS tid ORDER BY tid"
            ).data()
        return [self._get_technique_or_blank(r["tid"]) for r in recs]

    def add_relation(self, src: str, rel: str, dst: str) -> None:
        """添加关系边（两端节点已存在时；tactic 节点需已 seed）。

        Args:
            src: 源节点（tactic 名或 technique_id）。
            rel: 关系标签。
            dst: 目标节点。

        Raises:
            ValueError: rel 不在合法标签集合时。
        """
        if rel not in _ALLOWED_RELS:
            raise ValueError(f"非法关系标签: {rel}")
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run(
                f"MATCH (a) WHERE a.technique_id=$src OR a.name=$src "
                f"MATCH (b) WHERE b.technique_id=$dst OR b.name=$dst "
                f"MERGE (a)-[:{rel}]->(b)",
                src=src,
                dst=dst,
            )

    def related_techniques(
        self, technique_id: str, relation: str | None = None
    ) -> list[MemoryPacket]:
        """返回与指定技战术关联的其他技战术（双向）。"""
        rel_clause = f"-[r:{relation}]-" if relation else "-[r]-"
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run(
                f"MATCH (t:Technique {{technique_id: $tid}}){rel_clause}(n:Technique) "
                "RETURN n.technique_id AS tid",
                tid=technique_id,
            ).data()
        return [self._get_technique_or_blank(r["tid"]) for r in recs]

    def _get_technique_or_blank(self, technique_id: str) -> MemoryPacket:
        """按 ID 查技战术；查不到时返回空白包（避免二次查询失败）。

        Args:
            technique_id: 技战术 ID。

        Returns:
            MemoryPacket 或空白包。
        """
        p = self.get_technique(technique_id)
        return p if p is not None else MemoryPacket(task_id=technique_id, kind="decision")

    # ---- 网络拓扑 ----

    def save_topology(
        self, scope: str, assets: list[Asset], links: list[tuple[str, str, str]]
    ) -> None:
        """保存拓扑：删除旧 scope 节点后写入（MERGE 幂等）。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            session.run("MATCH (a:Asset {scope: $scope}) DETACH DELETE a", scope=scope)
            for asset in assets:
                session.run(
                    "MERGE (a:Asset {asset_id: $aid}) SET a.scope=$scope, a.host=$host, "
                    "a.os=$os, a.exposure=$exposure, a.services=$services",
                    aid=asset.asset_id,
                    scope=scope,
                    host=asset.host,
                    os=asset.os,
                    exposure=asset.exposure,
                    services=list(asset.services),
                )
            for src, rel, dst in links:
                session.run(
                    f"MATCH (a:Asset {{asset_id: $src}}), (b:Asset {{asset_id: $dst}}) "
                    f"MERGE (a)-[:{rel}]->(b)",
                    src=src,
                    dst=dst,
                )

    def get_topology(self, scope: str) -> tuple[list[Asset], list[tuple[str, str, str]]]:
        """读取指定作用域拓扑，还原为 (assets, links)。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            nodes = session.run("MATCH (a:Asset {scope: $scope}) RETURN a", scope=scope).data()
            links = session.run(
                "MATCH (a:Asset {scope: $scope})-[r]->(b:Asset) RETURN a.asset_id AS src, "
                "type(r) AS rel, b.asset_id AS dst",
                scope=scope,
            ).data()
        assets = [
            Asset(
                asset_id=n["a"]["asset_id"],
                host=n["a"].get("host", ""),
                os=n["a"].get("os", ""),
                exposure=n["a"].get("exposure", "external"),
                services=list(n["a"].get("services", [])),
            )
            for n in nodes
        ]
        return assets, [(lnk["src"], lnk["rel"], lnk["dst"]) for lnk in links]

    def list_topologies(self) -> list[str]:
        """返回全部已保存的拓扑作用域。"""
        driver = self._get_driver()
        with driver.session(database=self._database) as session:
            recs = session.run("MATCH (a:Asset) RETURN DISTINCT a.scope AS scope").data()
        return [r["scope"] for r in recs]
