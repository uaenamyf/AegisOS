# date: 2026-08-01
# dev: 123 chen
"""反馈闭环 —— 整合批判+评分 → FeedbackRecord → 写回记忆层。

将 :class:`ExecutionCritic` 和 :class:`OutputScorer` 的产出整合为
:class:`FeedbackRecord`，并写回 ``memory/reflection`` 的 ReflectionEngine
（tag_outcome + record_reference），形成认知自我改进闭环。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aegisos_agents.perception.reflection.critic import Critique, ExecutionCritic
from aegisos_agents.perception.reflection.scoring import OutputScore, OutputScorer

if TYPE_CHECKING:
    from aegisos_agents.memory.reflection.engine import ReflectionEngine


@dataclass
class FeedbackRecord:
    """反思反馈记录。

    Attributes:
        agent_id: 产生输出的 Agent 标识符。
        task_id: 关联的任务标识符。
        score: 四维评分结果。
        critiques: 批判条目列表。
        grade: 等级（success / pass / fail）。
        summary: 人类可读的反馈摘要。
    """

    agent_id: str = ""
    task_id: str = ""
    score: OutputScore = field(default_factory=OutputScore)
    critiques: list[Critique] = field(default_factory=list)
    grade: str = "pass"
    summary: str = ""


class FeedbackLoop:
    """反思反馈闭环 —— 批判 + 评分 + 写回记忆层。

    整合 :class:`ExecutionCritic` 和 :class:`OutputScorer`，产生
    :class:`FeedbackRecord` 后写回 ``memory/reflection`` 的
    :class:`ReflectionEngine`（如果提供），用于经验质量标记和引用计数更新。

    Attributes:
        _critic: 执行批判引擎。
        _scorer: 输出评分引擎。
    """

    def __init__(self) -> None:
        """初始化反馈闭环，装配批判与评分引擎。"""
        self._critic = ExecutionCritic()
        self._scorer = OutputScorer()

    # ---- 公开接口 ----

    def reflect(
        self,
        agent_id: str,
        task_id: str,
        output: dict,
        expected_fields: list[str] | None = None,
        input_context: dict | None = None,
        step_count: int = 1,
        reflection_engine: ReflectionEngine | None = None,
    ) -> FeedbackRecord:
        """对单次 Agent 执行结果做完整反思。

        流程：critique → score → FeedbackRecord → 写回 memory/reflection。

        Args:
            agent_id: 执行 Agent 标识符。
            task_id: 关联的任务标识符。
            output: Agent 执行的输出字典。
            expected_fields: 期望的字段列表，用于完整性与正确性评估。
            input_context: 原始输入上下文，用于一致性检查。
            step_count: 执行步骤数，用于效率评分。
            reflection_engine: 可选的记忆反思引擎，用于写回结果。

        Returns:
            :class:`FeedbackRecord`，含评分、批判与等级。
        """
        # 1) 批判
        critiques = self._critic.critique(output, expected_fields, input_context)
        # 2) 评分
        score = self._scorer.score(output, critiques, expected_fields, step_count)
        # 3) 生成摘要
        summary = self._make_summary(agent_id, task_id, score, critiques)
        # 4) 写回 memory/reflection
        if reflection_engine is not None and task_id:
            # 映射 grade → outcome
            outcome_map = {"success": "success", "pass": "unknown", "fail": "failure"}
            reflection_engine.tag_outcome(task_id, outcome_map.get(score.grade, "unknown"))
            reflection_engine.record_reference(task_id)
        return FeedbackRecord(
            agent_id=agent_id,
            task_id=task_id,
            score=score,
            critiques=critiques,
            grade=score.grade,
            summary=summary,
        )

    def batch_reflect(
        self,
        results: list[dict],
        reflection_engine: ReflectionEngine | None = None,
    ) -> list[FeedbackRecord]:
        """批量反思，对多个 Agent 产出依次评估。

        Args:
            results: 执行结果列表，每项含 agent_id / task_id / output / expected_fields / input_context / step_count。
            reflection_engine: 可选的记忆反思引擎。

        Returns:
            :class:`FeedbackRecord` 列表。
        """
        records: list[FeedbackRecord] = []
        for r in results:
            record = self.reflect(
                agent_id=r.get("agent_id", ""),
                task_id=r.get("task_id", ""),
                output=r.get("output", {}),
                expected_fields=r.get("expected_fields"),
                input_context=r.get("input_context"),
                step_count=r.get("step_count", 1),
                reflection_engine=reflection_engine,
            )
            records.append(record)
        return records

    # ---- 私有方法 ----

    @staticmethod
    def _make_summary(
        agent_id: str,
        task_id: str,
        score: OutputScore,
        critiques: list[Critique],
    ) -> str:
        """生成人类可读的反馈摘要。

        Args:
            agent_id: Agent 标识符。
            task_id: 任务标识符。
            score: 评分结果。
            critiques: 批判列表。

        Returns:
            摘要文本。
        """
        parts = [
            f"[{score.grade.upper()}] agent={agent_id} task={task_id}",
            f"overall={score.overall:.2f}",
            f"completeness={score.completeness:.2f}",
            f"correctness={score.correctness:.2f}",
        ]
        high_count = sum(1 for c in critiques if c.severity == "high")
        if high_count > 0:
            parts.append(f"blockers={high_count}")
        return " | ".join(parts)
