# date: 2026-09-13
# dev: OpenSquilla
# changelog: 新增记忆持久化模块——跨重启记忆保持（解决 memory 全内存、重启清零的短板）
"""记忆持久化存储。

把长期记忆的"不可再生"部分（情景经验、检查点、快照、工作记忆栈）落盘为
JSON 文件，支持重启后原样恢复，落实赛题"分布式记忆架构""跨会话记忆保持"
与"跨重启不丢失"的要求（见 MEMORY_REFACTOR_REPORT 问题 3）。

设计要点：
    - 零新依赖：JSON 序列化 ``MemoryPacket``（Pydantic model_dump），
      可切换到 SQLite/Qdrant 后端而不改接口。
    - 只持久化"用户/运行时产生、重启不可再生成"的数据：episodic（决策经验）、
      working（进行中会话的工作栈）、checkpoints、snapshots。
      semantic 知识库启动时由数据集重新 seed（可在内存中重建），不落盘。
    - 写盘是显式触发（``save()``），MemoryStore 在快照/演练结束等时机调用，
      避免每次写入都做同步 IO。
    - 通过 Checkpoint/Snapshot 管理器的公开 dump/restore_all 访问，不触及私有态。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from protocol.memory import MemoryPacket

if TYPE_CHECKING:
    from aegisos_agents.memory.memory_store import MemoryStore


class MemoryPersistence:
    """记忆持久化：``save(store)`` 落盘 / ``load(store)`` 恢复。

    Attributes:
        path: 落盘文件路径（UTF-8 JSON）。
    """

    def __init__(self, path: str | Path) -> None:
        """初始化持久化器。

        Args:
            path: 落盘文件路径；父目录不存在时自动创建。
        """
        self.path = Path(path)
        self._lock = threading.Lock()
        if self.path.parent and not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- 序列化 ----

    @staticmethod
    def _packet_list(packets: list[MemoryPacket]) -> list[dict]:
        """把记忆包列表序列化为可 JSON 化的 dict 列表。"""
        return [p.model_dump() for p in packets]

    @staticmethod
    def _restore_packets(data: list[dict] | None) -> list[MemoryPacket]:
        """从 dict 列表还原记忆包；跳过损坏条目并静默降级。"""
        packets: list[MemoryPacket] = []
        for d in data or []:
            try:
                packets.append(MemoryPacket.model_validate(d))
            except Exception:  # noqa: BLE001 —— 单条损坏不应阻断整体恢复
                continue
        return packets

    def snapshot_state(self, store: "MemoryStore") -> dict:
        """采集可持久化记忆状态（供 save 使用）。

        Args:
            store: 记忆集成存储实例。

        Returns:
            含 episodic / working / checkpoints / snapshots 的可序列化字典。
        """
        checkpoints = store.checkpoint.dump()
        snapshots = store.snapshot.dump()
        return {
            "version": 1,
            "episodic": self._packet_list(store.episodic.all()),
            "working": {
                sid: self._packet_list(store.working.get(sid))
                for sid in store.working.sessions()
            },
            "checkpoints": {sid: self._packet_list(ps) for sid, ps in checkpoints.items()},
            "snapshots": {
                oid: snapshots["snapshots"][oid].model_dump() for oid in snapshots["order"]
            },
            "_snapshot_order": snapshots["order"],
        }

    # ---- 落盘 ----

    def save(self, store: "MemoryStore") -> Path:
        """原子写入记忆状态到磁盘。

        Args:
            store: 记忆集成存储实例。

        Returns:
            写出的文件路径。
        """
        state = self.snapshot_state(store)
        tmp = self.path.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)  # 原子替换，避免写一半损坏
        return self.path

    # ---- 载入 ----

    def load(self, store: "MemoryStore") -> bool:
        """从磁盘恢复记忆状态到 store。

        Args:
            store: 记忆集成存储实例（将就地填充）。

        Returns:
            成功恢复返回 True；无文件或解析失败返回 False。
        """
        if not self.path.exists():
            return False
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False

        # 情景记忆（长期经验）——直接重建；携带 embedding 的同步重建向量索引，
        # 否则向量通道在持久化恢复后是"空转"的（vector_total 恒为 0）
        for p in self._restore_packets(raw.get("episodic")):
            store.episodic.add(p)
            if getattr(p, "embedding", None):
                try:
                    store.vector.add(p)
                except Exception:  # noqa: BLE001 —— 单条索引失败不阻断整体恢复
                    pass

        # 工作记忆栈——按会话回填
        for sid, entries in (raw.get("working") or {}).items():
            for p in self._restore_packets(entries):
                store.working.add(p)

        # 检查点——经公开 restore_all 重建
        checkpoints = {
            sid: self._restore_packets(entries)
            for sid, entries in (raw.get("checkpoints") or {}).items()
        }
        store.checkpoint.restore_all(checkpoints)

        # 快照——经公开 restore_all 重建
        snapshots = {
            oid: pkt
            for oid, d in (raw.get("snapshots") or {}).items()
            for pkt in [self._try_packet(d)]
            if pkt is not None
        }
        order = list(raw.get("_snapshot_order") or [])
        store.snapshot.restore_all({"snapshots": snapshots, "order": order})

        return True

    @staticmethod
    def _try_packet(d) -> MemoryPacket | None:
        """尝试还原单个快照包；失败返回 None。"""
        try:
            return MemoryPacket.model_validate(d)
        except Exception:  # noqa: BLE001
            return None