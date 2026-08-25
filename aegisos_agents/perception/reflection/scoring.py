# date: 2026-08-01
# dev: 123 chen
"""输出评分 —— 对 Agent 产出做四维量化评分。

纯算法实现：完整性 × 正确性 × 效率 × 安全性四维评分，
加权综合后产生 :class:`OutputScore` 与等级（success/pass/fail）。
"""

from __future__ import annotations

from dataclasses import dataclass

from aegisos_agents.perception.reflection.critic import Critique

# 评分维度权重
WEIGHT_COMPLETENESS = 0.3
WEIGHT_CORRECTNESS = 0.3
WEIGHT_EFFICIENCY = 0.2
WEIGHT_SAFETY = 0.2


@dataclass
class OutputScore:
    """Agent 产出评分结果。

    Attributes:
        completeness: 完整性评分 [0.0, 1.0]（字段填充率）。
        correctness: 正确性评分 [0.0, 1.0]（批判问题越少分越高）。
        efficiency: 效率评分 [0.0, 1.0]（步骤数/冗余度）。
        safety: 安全性评分 [0.0, 1.0]（破坏性标记加权）。
        overall: 加权综合分 [0.0, 1.0]。
        grade: 等级：success(>=0.7) / pass(>=0.5) / fail(<0.5)。
    """

    completeness: float = 1.0
    correctness: float = 1.0
    efficiency: float = 1.0
    safety: float = 1.0
    overall: float = 1.0
    grade: str = "success"


class OutputScorer:
    """对 Agent 产出做四维量化评分。

    评分维度：
        - 完整性：预期字段的填充率。
        - 正确性：批判问题数量越少分越高。
        - 效率：步骤数/冗余度影响。
        - 安全性：是否存在破坏性操作标记。

    Attributes:
        无实例属性；本类为纯函数集合。
    """

    def score(
        self,
        output: dict,
        critiques: list[Critique],
        expected_fields: list[str] | None = None,
        step_count: int = 1,
    ) -> OutputScore:
        """四维评分，产生完整评分结果。

        Args:
            output: Agent 执行输出的字典。
            critiques: :class:`ExecutionCritic.critique` 产生的批判列表。
            expected_fields: 期望字段列表，用于完整性评分。
            step_count: 执行步骤数，用于效率评分。

        Returns:
            :class:`OutputScore` 评分结果。
        """
        completeness = self._score_completeness(output, expected_fields or [])
        correctness = self._score_correctness(critiques)
        efficiency = self._score_efficiency(step_count)
        safety = self._score_safety(critiques)
        overall = (
            WEIGHT_COMPLETENESS * completeness
            + WEIGHT_CORRECTNESS * correctness
            + WEIGHT_EFFICIENCY * efficiency
            + WEIGHT_SAFETY * safety
        )
        # 等级判定
        if overall >= 0.7:
            grade = "success"
        elif overall >= 0.5:
            grade = "pass"
        else:
            grade = "fail"
        return OutputScore(
            completeness=completeness,
            correctness=correctness,
            efficiency=efficiency,
            safety=safety,
            overall=overall,
            grade=grade,
        )

    def quick_score(self, output: dict, expected_fields: list[str] | None = None) -> OutputScore:
        """快速评分，不依赖批判列表（仅 completeness + safety 基础分）。

        Args:
            output: Agent 执行输出的字典。
            expected_fields: 期望字段列表。

        Returns:
            :class:`OutputScore` 快速评分结果。
        """
        completeness = self._score_completeness(output, expected_fields or [])
        safety = 1.0  # 无批判数据时默认安全
        overall = WEIGHT_COMPLETENESS * completeness + WEIGHT_SAFETY * safety
        if overall >= 0.7:
            grade = "success"
        elif overall >= 0.5:
            grade = "pass"
        else:
            grade = "fail"
        return OutputScore(
            completeness=completeness,
            correctness=1.0,  # 无数据默认满分
            efficiency=1.0,
            safety=safety,
            overall=overall,
            grade=grade,
        )

    # ---- 私有评分方法 ----

    def _score_completeness(self, output: dict, expected_fields: list[str]) -> float:
        """计算字段填充率。

        Args:
            output: 输出字典。
            expected_fields: 期望字段列表。

        Returns:
            填充率 [0.0, 1.0]；无期望字段时返回 1.0。
        """
        if not expected_fields:
            return 1.0
        filled = sum(1 for f in expected_fields if output.get(f) not in (None, "", [], {}))
        return filled / len(expected_fields)

    @staticmethod
    def _score_correctness(critiques: list[Critique]) -> float:
        """根据批判问题数量计算正确性分。

        Args:
            critiques: 批判列表。

        Returns:
            正确性分 [0.0, 1.0]；10 个问题以上归零。
        """
        if not critiques:
            return 1.0
        # 高严重度问题权重加倍
        weighted = sum(2 if c.severity == "high" else 1 for c in critiques)
        return max(1.0 - weighted / 10.0, 0.0)

    @staticmethod
    def _score_efficiency(step_count: int) -> float:
        """根据步骤数计算效率分。

        Args:
            step_count: 执行步骤数。

        Returns:
            效率分 [0.0, 1.0]；1 步满分，10 步以上趋近于零。
        """
        return 1.0 / (1.0 + max(step_count - 1, 0) / 10.0)

    @staticmethod
    def _score_safety(critiques: list[Critique]) -> float:
        """根据破坏性操作标记计算安全分。

        Args:
            critiques: 批判列表。

        Returns:
            安全分 [0.0, 1.0]；每出现一个破坏性标记扣 0.5。
        """
        destructive = [
            c for c in critiques
            if c.field == "action" and "破坏性操作" in c.message
        ]
        if not destructive:
            return 1.0
        return max(1.0 - 0.5 * len(destructive), 0.0)
