# date: 2026-08-01
# dev: 123 chen
"""Token 预算与裁剪 —— 上下文窗口管理组件。

提供 token 估算（字符数/4 经验公式）与智能裁剪策略：
决策+最近步优先保留，其余按头尾各半截断并生成 digest 摘要。
"""

from __future__ import annotations

from protocol.memory import MemoryPacket


class TokenBudget:
    """Token 预算估算与智能裁剪。

    用于控制每个 Agent 推理请求的上下文长度，避免超出模型上下文窗口。
    裁剪策略：保留决策+最近步 → 头尾各半截断 → 生成 digest 摘要。

    Attributes:
        _default_budget: 默认 token 预算（4096，约 16K 字符）。
    """

    def __init__(self, default_budget: int = 4096) -> None:
        """初始化 TokenBudget。

        Args:
            default_budget: 默认 token 预算上限，默认 4096。
        """
        self._default_budget = default_budget

    # ---- 估算 ----

    @staticmethod
    def estimate(text: str) -> int:
        """估算单段文本的 token 数。

        采用"字符数 / 4 + 1"的经验公式（近似英文 1 token ≈ 4 字符）。

        Args:
            text: 待估算的文本。

        Returns:
            估算得到的 token 数，最小为 1。
        """
        return len(text) // 4 + 1

    def estimate_packets(self, packets: list[MemoryPacket]) -> int:
        """估算 MemoryPacket 列表的总 token 使用量。

        汇总每条记忆的 summary、working、episodic 三个字段。

        Args:
            packets: 待估算的记忆列表。

        Returns:
            估算的 token 总量。
        """
        total = 0
        for pkt in packets:
            total += self.estimate(str(pkt.summary))
            total += self.estimate(str(pkt.working))
            total += self.estimate(str(pkt.episodic))
        return total

    # ---- 裁剪 ----

    def trim(
        self, packets: list[MemoryPacket], budget: int | None = None
    ) -> list[MemoryPacket]:
        """在 token 预算内裁剪记忆列表。

        裁剪策略：
            1. 未超预算 → 原样返回。
            2. 优先保留 recent=True 或 kind="decision" 的记忆。
            3. 剩余仍超预算 → 头尾各保留一条，中间压缩为 digest 摘要。

        Args:
            packets: 待裁剪的记忆列表（按写入时序排列）。
            budget: 允许的最大 token 数，默认使用 ``_default_budget``。

        Returns:
            裁剪后的记忆列表，可能包含一条 truncation digest。
        """
        if not packets:
            return []
        limit = budget if budget is not None else self._default_budget
        if self.estimate_packets(packets) <= limit:
            return packets
        # 1) 保留重要记忆：最近步 + 决策类
        keep = [m for m in packets if m.recent or m.kind == "decision"]
        rest = [m for m in packets if m not in keep]
        if not rest:
            return keep
        # 2) 头尾各保留 1 条，其余压缩为 digest
        if len(rest) <= 2:
            return keep + rest  # 不足 3 条时全部保留
        head, tail = rest[0], rest[-1]
        middle_ids = [m.task_id or str(i) for i, m in enumerate(rest[1:-1])]
        digest = MemoryPacket(
            task_id="truncation",
            kind="digest",
            summary=" | ".join(
                (m.summary or m.task_id or "?") for m in rest[1:-1]
            ),
            compression={
                "count": len(rest[1:-1]),
                "ids": middle_ids,
                "reason": "token_budget_trim",
            },
        )
        return keep + [head, digest, tail]
