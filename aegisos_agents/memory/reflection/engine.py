# date: 2026-08-01
# dev: myf
"""反思引擎 —— 经验质量评估。

对情景记忆中的决策类记忆（kind=decision）做三维评估：
时效性（freshness）× 引用频次（reference_count）× 结果标记（outcome）。
纯算法实现，不依赖 LLM 调用。用于 recall 结果重排序，使优质经验优先。
"""

from __future__ import annotations

import time

from protocol.memory import MemoryPacket

# 评估维度权重
WEIGHT_FRESHNESS = 0.3
WEIGHT_REFERENCE = 0.3
WEIGHT_OUTCOME = 0.4

# 结果标记映射为评分系数
OUTCOME_SCORES = {"success": 1.0, "unknown": 0.5, "failure": 0.0}

# 时效性衰减半衰期（秒）—— 1 小时
FRESHNESS_HALF_LIFE = 3600.0


class ReflectionEngine:
    """反思引擎 —— 三维经验质量评估。

    对决策类记忆按 **时效性 × 引用频次 × 结果标记** 三维度加权评分，
    用于在 recall 时重排序候选记忆，确保优质经验优先注入推理上下文。

    Attributes:
        _outcomes: {task_id -> outcome} 结果标记（success/failure/unknown）。
        _reference_counts: {task_id -> count} 引用计数器。
        _creation_times: {task_id -> timestamp} 记忆创建时间（monotonic）。
    """

    def __init__(self) -> None:
        """初始化反思引擎，空的评估记录。"""
        self._outcomes: dict[str, str] = {}
        self._reference_counts: dict[str, int] = {}
        self._creation_times: dict[str, float] = {}

    # ---- 公开接口 ----

    def evaluate(self, packet: MemoryPacket) -> float:
        """对单条记忆做三维评估评分。

        评分公式：
            score = 0.3 × freshness + 0.3 × ref_score + 0.4 × outcome
        其中 freshness = 1.0 / (1 + age / half_life)。

        Args:
            packet: 待评估的记忆包。

        Returns:
            综合评分（[0.0, 1.0] 区间）。
        """
        task_id = packet.task_id or ""
        if not task_id:
            return 0.5  # 无 task_id 的记忆给中性分
        # 记录创建时间（首次调用）
        if task_id not in self._creation_times:
            self._creation_times[task_id] = time.monotonic()
        age = time.monotonic() - self._creation_times[task_id]
        freshness = 1.0 / (1.0 + age / FRESHNESS_HALF_LIFE)
        ref_count = self._reference_counts.get(task_id, 0)
        ref_score = min(ref_count / 10.0, 1.0)
        outcome = self._outcomes.get(task_id, "unknown")
        outcome_score = OUTCOME_SCORES.get(outcome, 0.5)
        return (
            WEIGHT_FRESHNESS * freshness
            + WEIGHT_REFERENCE * ref_score
            + WEIGHT_OUTCOME * outcome_score
        )

    def rank(self, memories: list[MemoryPacket]) -> list[tuple[MemoryPacket, float]]:
        """批量评估并按评分降序排列。

        Args:
            memories: 待排序的记忆列表。

        Returns:
            ``(MemoryPacket, score)`` 列表，按评分降序。
        """
        scored = [(m, self.evaluate(m)) for m in memories]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def tag_outcome(self, task_id: str, outcome: str) -> None:
        """标注记忆的执行结果。

        Args:
            task_id: 目标任务标识符。
            outcome: ``"success"`` / ``"failure"`` / ``"unknown"``。
        """
        if outcome in OUTCOME_SCORES:
            self._outcomes[task_id] = outcome

    def record_reference(self, task_id: str) -> None:
        """记录一次对某条记忆的引用（召回命中）。

        Args:
            task_id: 被引用的任务标识符。
        """
        self._reference_counts[task_id] = self._reference_counts.get(task_id, 0) + 1

    def get_reference_count(self, task_id: str) -> int:
        """查询引用次数。

        Args:
            task_id: 目标任务标识符。

        Returns:
            引用计数，未记录过返回 0。
        """
        return self._reference_counts.get(task_id, 0)

    def is_cold(self, task_id: str, threshold: int = 0) -> bool:
        """判断某条记忆是否为"冷"记忆（引用次数 ≤ 阈值）。

        用于 archive 模块判断是否应下沉冷数据。

        Args:
            task_id: 目标任务标识符。
            threshold: 冷数据判断阈值，默认 0（从未被引用即为冷）。

        Returns:
            ``True`` 表示冷记忆（可归档）。
        """
        return self.get_reference_count(task_id) <= threshold

    def stats(self) -> dict:
        """返回评估统计信息。

        Returns:
            含 total_evaluated / success_count / failure_count / unknown_count 的字典。
        """
        outcomes = list(self._outcomes.values())
        return {
            "total_evaluated": len(self._outcomes),
            "success_count": outcomes.count("success"),
            "failure_count": outcomes.count("failure"),
            "unknown_count": outcomes.count("unknown"),
        }
