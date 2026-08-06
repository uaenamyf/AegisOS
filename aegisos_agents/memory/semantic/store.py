# date: 2026-07-06
# dev: myf
"""语义记忆存储模块。

语义记忆即"知识库"：长期、结构化的事实与概念图谱，跨会话持久。
本模块以 ``concept_id -> MemoryPacket`` 维护知识条目，``MemoryPacket.semantic``
字段承载结构化事实（如 ATT&CK 技战术 ID / CVE 编号 / 描述 / 对抗措施）。
预置少量 ATT&CK 种子知识，供神经符号闭环与 threat_hunt 等 Agent 查询。

设计要点：
    - 纯内存 dict，按 concept_id 精确查；关键词检索在 semantic 字段值中做子串匹配。
    - ``seed_attack_knowledge`` 预置 ATT&CK 常见技战术，覆盖红队侦察/利用/横向移动与
      蓝队检测/响应，作为赛事演示的最小知识基底。
    - 未来可对接 Neo4j ATT&CK 图（H2），本模块为接口稳定的预留位。
"""

from __future__ import annotations

from data.api import GraphStoreAPI, load_attck_dataset
from protocol.memory import MemoryPacket

# ATT&CK 种子知识：technique_id -> (名称, 战术阶段, 描述)
# 覆盖赛事场景 1（网络防御）所需的最小技战术集合。
_ATTACK_SEED: dict[str, tuple[str, str, str]] = {
    "T1595": ("Active Scanning", "reconnaissance", "主动扫描目标收集可利用信息"),
    "T1592": ("Gather Victim Host Info", "reconnaissance", "收集目标主机配置/操作系统/软件信息"),
    "T1210": (
        "Exploitation of Remote Services",
        "lateral-movement",
        "利用远程服务漏洞进行横向移动",
    ),
    "T1059": ("Command and Scripting Interpreter", "execution", "通过命令脚本解释器执行恶意代码"),
    "T1078": ("Valid Accounts", "defense-evasion", "利用合法账户凭证规避检测"),
    "T1046": ("Network Service Discovery", "discovery", "发现网络中可用的服务"),
    "T1021": ("Remote Services", "lateral-movement", "通过远程服务（SSH/SMB/RDP）横向移动"),
    "T1053": ("Scheduled Task/Job", "execution", "通过计划任务持久化执行"),
}


class SemanticMemory:
    """语义记忆存储 —— 结构化知识库（ATT&CK/CVE）。

    默认内存 dict + 种子；传入 :class:`GraphStoreAPI` 后端时，
    读写委托给图存储（ATT&CK 知识查询走后端）。

    Attributes:
        _backend: 可选的外部图存储后端。
        _knowledge: 内部维护的 concept_id -> 知识记忆包。
    """

    def __init__(self, seed: bool = True, graph_backend: GraphStoreAPI | None = None) -> None:
        """初始化语义记忆存储。

        Args:
            seed: 是否在构造时预置 ATT&CK 知识，默认 ``True``。
            graph_backend: 可选的外部图存储后端；为 None 时用内置内存实现。
        """
        self._backend = graph_backend
        self._knowledge: dict[str, MemoryPacket] = {}
        if graph_backend is None:
            if seed:
                self.seed_attack_knowledge()
        elif seed and not graph_backend.all_techniques():
            # 后端为空时从共享数据集预载，避免首次查询退化
            graph_backend.seed_attck(load_attck_dataset())

    def add(self, concept_id: str, packet: MemoryPacket) -> None:
        """写入或覆盖一条知识条目。

        Args:
            concept_id: 知识概念唯一标识（如 ATT&CK 技战术 ID ``T1210``）。
            packet: 知识记忆包，其 ``semantic`` 字段承载结构化事实。
        """
        if self._backend is not None:
            self._backend.upsert_technique(concept_id, packet)
            return
        self._knowledge[concept_id] = packet

    def get(self, concept_id: str) -> MemoryPacket | None:
        """按概念 ID 精确查询知识条目。

        Args:
            concept_id: 目标概念标识符。

        Returns:
            匹配的知识记忆包；未找到时返回 ``None``。
        """
        if self._backend is not None:
            return self._backend.get_technique(concept_id)
        return self._knowledge.get(concept_id)

    def search(self, keyword: str) -> list[MemoryPacket]:
        """关键词检索知识库（大小写不敏感）。

        后端存在时委托图存储检索；否则在每条知识的 ``semantic`` 字段
        各值与 ``summary`` 中做子串匹配。

        Args:
            keyword: 检索关键词，如 ``"lateral"``、``"扫描"``。

        Returns:
            命中的知识记忆包列表。
        """
        if self._backend is not None:
            return self._backend.search_techniques(keyword)
        kw = keyword.lower()
        hits: list[MemoryPacket] = []
        for packet in self._knowledge.values():
            # summary 文本匹配
            if kw in (packet.summary or "").lower():
                hits.append(packet)
                continue
            # semantic 字典各值文本匹配
            for v in packet.semantic.values():
                if kw in str(v).lower():
                    hits.append(packet)
                    break
        return hits

    def all(self) -> list[MemoryPacket]:
        """返回全部知识条目。"""
        if self._backend is not None:
            return self._backend.all_techniques()
        return list(self._knowledge.values())

    def seed_attack_knowledge(self) -> None:
        """预置 ATT&CK 种子技战术知识。

        将 :data:`_ATTACK_SEED` 中的技战术转化为 ``MemoryPacket`` 写入存储，
        每条的 ``semantic`` 字段含 technique_id/name/tactic/description。
        """
        for tid, (name, tactic, desc) in _ATTACK_SEED.items():
            self._knowledge[tid] = MemoryPacket(
                task_id=tid,
                summary=f"{tid} {name}",
                semantic={
                    "technique_id": tid,
                    "name": name,
                    "tactic": tactic,
                    "description": desc,
                },
                kind="decision",  # 知识库条目视为决策级（检索时优先）
            )

    def __len__(self) -> int:
        """返回知识条目总数。"""
        if self._backend is not None:
            return len(self._backend.all_techniques())
        return len(self._knowledge)
