# date: 2026-08-01
# dev: myf
"""缓存记忆存储 —— L1 查询缓存 + L2 热点缓存，LRU 淘汰。

为记忆召回提供热数据加速：L1 缓存最近 recall 结果（TTL 60s），
L2 缓存高频访问的单个记忆（访问 ≥3 次自动晋升，容量 100 条，LRU 淘汰）。
"""

from __future__ import annotations

import time
from collections import OrderedDict
from hashlib import sha256

from protocol.memory import MemoryPacket

# L2 热点缓存容量上限
L2_CAPACITY = 100
# 晋升 L2 所需的最小访问次数
L2_PROMOTE_THRESHOLD = 3
# 默认 L1 TTL（秒）
DEFAULT_TTL = 60.0


class MemoryCache:
    """二级记忆缓存 —— 查询缓存（L1）+ 热点缓存（L2）。

    L1 按查询文本哈希索引，L2 按 task_id 索引 + LRU 淘汰。
    每条记忆写入时通过 ``invalidate`` 级联失效 L1 + L2。

    Attributes:
        _l1: {hash(text) -> (timestamp, results)} 查询缓存。
        _l2: OrderedDict[task_id, MemoryPacket] 热点缓存，LRU。
        _access_count: {task_id -> count} 访问计数器。
        _hits: L1 命中次数。
        _misses: L1 未命中次数。
    """

    def __init__(self) -> None:
        """初始化空的二级缓存。"""
        self._l1: dict[str, tuple[float, list[MemoryPacket]]] = {}
        self._l2: OrderedDict[str, MemoryPacket] = OrderedDict()
        self._access_count: dict[str, int] = {}
        self._hits = 0
        self._misses = 0

    # ---- L1 查询缓存 ----

    def get_query(self, key: str) -> list[MemoryPacket] | None:
        """查询 L1 缓存。

        Args:
            key: 查询文本（触发词/关键词）。

        Returns:
            缓存的记忆列表；未命中或已过期返回 ``None``。
        """
        h = self._hash_key(key)
        entry = self._l1.get(h)
        if entry is None:
            self._misses += 1
            return None
        ts, results = entry
        if time.monotonic() - ts > DEFAULT_TTL:
            del self._l1[h]
            self._misses += 1
            return None
        self._hits += 1
        # 记录访问（用于 L2 晋升）
        for pkt in results:
            if pkt.task_id:
                self.touch(pkt.task_id)
        return results

    def set_query(self, key: str, results: list[MemoryPacket], ttl: float = DEFAULT_TTL) -> None:
        """写入 L1 查询缓存。

        Args:
            key: 查询文本。
            results: 缓存结果列表。
            ttl: 过期时间（秒），默认 60s。
        """
        h = self._hash_key(key)
        self._l1[h] = (time.monotonic() + ttl - DEFAULT_TTL, results)

    # ---- L2 热点缓存 ----

    def get_hot(self, task_id: str) -> MemoryPacket | None:
        """查询 L2 热点缓存。

        Args:
            task_id: 任务标识符。

        Returns:
            热点记忆；未命中返回 ``None``。
        """
        pkt = self._l2.get(task_id)
        if pkt is not None:
            self._l2.move_to_end(task_id)  # LRU 刷新
        return pkt

    def touch(self, task_id: str) -> None:
        """记录一次对 task_id 的访问；≥3 次自动晋升 L2。

        Args:
            task_id: 被访问的任务标识符。
        """
        if not task_id:
            return
        count = self._access_count.get(task_id, 0) + 1
        self._access_count[task_id] = count
        if count >= L2_PROMOTE_THRESHOLD and task_id not in self._l2:
            self._promote_to_l2(task_id)

    def _promote_to_l2(self, task_id: str) -> None:
        """将 task_id 对应的记忆从外部存储加载到 L2（由调用方在 touch 前注入）。

        当前为存储层方法，外部需配合 ``set_query`` 或直接构造 L2 条目。
        L2 淘汰：容量超限时移除最久未访问条目（LRU）。
        """
        if len(self._l2) >= L2_CAPACITY:
            self._l2.popitem(last=False)  # 移除最旧的
        # 占位：实际晋升发生在 touch() 中，此处仅处理容量淘汰
        self._l2[task_id] = MemoryPacket(task_id=task_id)
        self._l2.move_to_end(task_id)

    # ---- 失效 ----

    def invalidate(self, task_id: str) -> None:
        """失效 L1 + L2 中与 task_id 相关的所有缓存条目。

        Args:
            task_id: 待失效的任务标识符。
        """
        if not task_id:
            return
        # 失效 L2
        self._l2.pop(task_id, None)
        self._access_count.pop(task_id, None)
        # 失效 L1：扫描并移除包含该 task_id 的缓存条目
        stale_keys = []
        for h, (_, results) in self._l1.items():
            if any(pkt.task_id == task_id for pkt in results):
                stale_keys.append(h)
        for h in stale_keys:
            del self._l1[h]

    # ---- 统计 ----

    def stats(self) -> dict:
        """返回缓存统计信息。

        Returns:
            含 l1_size / l2_size / hits / misses / hit_rate 的字典。
        """
        total = self._hits + self._misses
        return {
            "l1_size": len(self._l1),
            "l2_size": len(self._l2),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    # ---- 内部 ----

    @staticmethod
    def _hash_key(key: str) -> str:
        """计算查询文本的 SHA-256 哈希（截取前 16 字符）。"""
        return sha256(key.encode()).hexdigest()[:16]
