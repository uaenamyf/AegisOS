# date: 2026-07-07
# dev: myf
# changelog: H5.4 新建 5 维度评测——accuracy/recall/latency/resource/robustness metrics + scorers + EvaluationReport
"""5 维度评测 —— 对齐赛题评分维度的评估指标、评分器与报告。

本模块实现对齐赛题评分维度的 5 维度评测：
    1. **准确率（accuracy）**：Agent 产出与预期匹配的比例。
    2. **召回率（recall）**：预期产出中被 Agent 正确产出的比例。
    3. **延迟（latency）**：Agent 执行耗时（来自 BenchmarkReport）。
    4. **资源（resource）**：Token 用量 / 调用次数 / 通信熵。
    5. **鲁棒性（robustness）**：异常输入下的成功率 / 降级能力。

设计要点：
    - **Metric**：单个指标值，含 name / value / weight（权重）。
    - **Scorer**：评分器，对原始指标按评分函数打分（0-100）。
    - **EvaluationReport**：评测报告，含 5 维度得分 + 总分 + 明细。

与现有架构的关系：
    - 实现 :class:`observability.api.EvaluationAPI` Protocol。
    - 消费 :class:`BenchmarkReport` 的延迟 / 成功率数据。
    - 对齐赛题评分维度（完整性 40% / 应用创新 25% / 技术创新 20% / 性能 15%）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pydantic import BaseModel
_asdict = lambda obj: obj.model_dump() if isinstance(obj, BaseModel) else obj
from typing import Any, Callable

import json


@dataclass
class Metric:
    """单个评测指标。

    Attributes:
        name: 指标名（如 ``"accuracy"`` / ``"latency_avg_ms"``）。
        value: 指标原始值。
        weight: 评分权重（0.0-1.0，用于加权总分）。
        description: 指标描述。
    """

    name: str
    value: float
    weight: float = 1.0
    description: str = ""


@dataclass
class DimensionScore:
    """单个评分维度的得分。

    Attributes:
        dimension: 维度名（``accuracy`` / ``recall`` / ``latency`` / ``resource`` / ``robustness``）。
        score: 得分（0-100）。
        weight: 该维度在总分中的权重。
        metrics: 该维度下的指标列表。
        notes: 评分说明。
    """

    dimension: str
    score: float = 0.0
    weight: float = 0.2
    metrics: list[Metric] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 2),
            "weight": self.weight,
            "metrics": [_asdict(m) for m in self.metrics],
            "notes": self.notes,
        }


@dataclass
class EvaluationReport:
    """评测报告 —— 5 维度评测汇总。

    Attributes:
        run_id: 评测运行 ID。
        dimensions: 5 个维度的得分列表。
        total_score: 加权总分（0-100）。
        summary: 文字摘要。
        started_at: 开始时间戳。
    """

    run_id: str = ""
    dimensions: list[DimensionScore] = field(default_factory=list)
    total_score: float = 0.0
    summary: str = ""
    started_at: float = 0.0

    @property
    def dimension_map(self) -> dict[str, DimensionScore]:
        """维度名 -> 得分的映射。"""
        return {d.dimension: d for d in self.dimensions}

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "total_score": round(self.total_score, 2),
            "summary": self.summary,
            "started_at": self.started_at,
            "dimensions": [d.to_dict() for d in self.dimensions],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False, indent=2)


# ---- 评分函数 ----


def score_accuracy(value: float, target: float = 1.0) -> float:
    """准确率评分：value 越接近 target 得分越高（线性映射到 0-100）。

    Args:
        value: 实际准确率（0.0-1.0）。
        target: 目标准确率（默认 1.0）。

    Returns:
        0-100 分。
    """
    return min(100.0, max(0.0, (value / target) * 100.0))


def score_recall(value: float, target: float = 0.8) -> float:
    """召回率评分。

    Args:
        value: 实际召回率（0.0-1.0）。
        target: 目标召回率（默认 0.8）。

    Returns:
        0-100 分。
    """
    return min(100.0, max(0.0, (value / target) * 100.0))


def score_latency(value_ms: float, target_ms: float = 5000.0) -> float:
    """延迟评分：延迟越低得分越高（线性反比，target_ms 为满分基准）。

    Args:
        value_ms: 实际延迟（毫秒）。
        target_ms: 满分基准延迟（默认 5000ms，低于此得满分）。

    Returns:
        0-100 分。
    """
    if value_ms <= 0:
        return 100.0
    return min(100.0, max(0.0, (target_ms / value_ms) * 100.0))


def score_resource(value: float, target: float = 10000.0) -> float:
    """资源评分：Token/调用次数越少得分越高。

    Args:
        value: 实际资源消耗（如 Token 总数）。
        target: 满分基准（默认 10000，低于此得满分）。

    Returns:
        0-100 分。
    """
    if value <= 0:
        return 100.0
    return min(100.0, max(0.0, (target / value) * 100.0))


def score_robustness(value: float, target: float = 0.9) -> float:
    """鲁棒性评分：异常下成功率越高得分越高。

    Args:
        value: 异常输入下的成功率（0.0-1.0）。
        target: 目标鲁棒性（默认 0.9）。

    Returns:
        0-100 分。
    """
    return min(100.0, max(0.0, (value / target) * 100.0))


class Evaluator:
    """评测器 —— 对齐赛题 5 维度评分。

    实现 :class:`observability.api.EvaluationAPI` Protocol。接收原始指标，
    按 5 维度评分并生成 :class:`EvaluationReport`。

    维度默认权重（对齐赛题评分占比）：
        - accuracy: 30%（完整性核心）
        - recall: 20%（完整性）
        - latency: 15%（性能）
        - resource: 15%（性能）
        - robustness: 20%（技术创新）
    """

    DEFAULT_WEIGHTS: dict[str, float] = {
        "accuracy": 0.30,
        "recall": 0.20,
        "latency": 0.15,
        "resource": 0.15,
        "robustness": 0.20,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """初始化评测器。

        Args:
            weights: 可选的自定义维度权重；None 用默认权重。
        """
        self._weights = weights or dict(self.DEFAULT_WEIGHTS)
        self._reports: dict[str, EvaluationReport] = {}

    def evaluate(
        self,
        run_id: str,
        accuracy: float = 1.0,
        recall: float = 1.0,
        latency_avg_ms: float = 0.0,
        token_count: float = 0.0,
        robustness_rate: float = 1.0,
        notes: dict[str, str] | None = None,
    ) -> EvaluationReport:
        """执行 5 维度评测。

        Args:
            run_id: 评测运行 ID。
            accuracy: 准确率（0.0-1.0）。
            recall: 召回率（0.0-1.0）。
            latency_avg_ms: 平均延迟（毫秒）。
            token_count: Token 总消耗。
            robustness_rate: 鲁棒性成功率（0.0-1.0）。
            notes: 可选的各维度评分说明。

        Returns:
            :class:`EvaluationReport`。
        """
        notes = notes or {}
        dimensions: list[DimensionScore] = []

        # 准确率维度
        acc_metric = Metric("accuracy", accuracy, 1.0, "Agent 产出与预期匹配比例")
        acc_score = score_accuracy(accuracy)
        dimensions.append(
            DimensionScore(
                dimension="accuracy",
                score=acc_score,
                weight=self._weights.get("accuracy", 0.30),
                metrics=[acc_metric],
                notes=notes.get("accuracy", ""),
            )
        )

        # 召回率维度
        rec_metric = Metric("recall", recall, 1.0, "预期产出中被正确产出的比例")
        rec_score = score_recall(recall)
        dimensions.append(
            DimensionScore(
                dimension="recall",
                score=rec_score,
                weight=self._weights.get("recall", 0.20),
                metrics=[rec_metric],
                notes=notes.get("recall", ""),
            )
        )

        # 延迟维度
        lat_metric = Metric("latency_avg_ms", latency_avg_ms, 1.0, "平均执行延迟（毫秒）")
        lat_score = score_latency(latency_avg_ms)
        dimensions.append(
            DimensionScore(
                dimension="latency",
                score=lat_score,
                weight=self._weights.get("latency", 0.15),
                metrics=[lat_metric],
                notes=notes.get("latency", ""),
            )
        )

        # 资源维度
        res_metric = Metric("token_count", token_count, 1.0, "Token 总消耗")
        res_score = score_resource(token_count)
        dimensions.append(
            DimensionScore(
                dimension="resource",
                score=res_score,
                weight=self._weights.get("resource", 0.15),
                metrics=[res_metric],
                notes=notes.get("resource", ""),
            )
        )

        # 鲁棒性维度
        rob_metric = Metric("robustness_rate", robustness_rate, 1.0, "异常输入下成功率")
        rob_score = score_robustness(robustness_rate)
        dimensions.append(
            DimensionScore(
                dimension="robustness",
                score=rob_score,
                weight=self._weights.get("robustness", 0.20),
                metrics=[rob_metric],
                notes=notes.get("robustness", ""),
            )
        )

        # 加权总分
        total = sum(d.score * d.weight for d in dimensions)

        report = EvaluationReport(
            run_id=run_id,
            dimensions=dimensions,
            total_score=total,
            summary=self._build_summary(dimensions, total),
        )
        self._reports[run_id] = report
        return report

    @staticmethod
    def _build_summary(dimensions: list[DimensionScore], total: float) -> str:
        """生成文字摘要。"""
        lines = [f"Total score: {total:.1f}/100"]
        for d in dimensions:
            lines.append(f"  {d.dimension}: {d.score:.1f} (weight: {d.weight:.0%})")
        return "\n".join(lines)

    def get_report(self, run_id: str) -> dict[str, Any] | None:
        """获取历史评测报告（兼容 EvaluationAPI）。

        Args:
            run_id: 运行 ID。

        Returns:
            报告字典；不存在返回 None。
        """
        report = self._reports.get(run_id)
        return report.to_dict() if report else None

    def evaluate_from_benchmark(
        self,
        run_id: str,
        benchmark_report: Any,
        accuracy: float = 1.0,
        recall: float = 1.0,
        token_count: float = 0.0,
        robustness_rate: float = 1.0,
    ) -> EvaluationReport:
        """从 BenchmarkReport 提取延迟与成功率，补充其他维度后评测。

        Args:
            run_id: 评测运行 ID。
            benchmark_report: :class:`BenchmarkReport` 实例。
            accuracy: 准确率（外部提供）。
            recall: 召回率（外部提供）。
            token_count: Token 总消耗。
            robustness_rate: 鲁棒性成功率。

        Returns:
            :class:`EvaluationReport`。
        """
        # 从 benchmark 提取平均延迟
        latency_avg_ms = 0.0
        if benchmark_report.case_stats:
            latency_avg_ms = statistics_mean([s.latency_avg_ms for s in benchmark_report.case_stats])
        # 从 benchmark 提取成功率作为鲁棒性参考
        if robustness_rate == 1.0 and benchmark_report.case_stats:
            success_rates = [s.success_rate for s in benchmark_report.case_stats]
            robustness_rate = statistics_mean(success_rates) if success_rates else 1.0
        return self.evaluate(
            run_id=run_id,
            accuracy=accuracy,
            recall=recall,
            latency_avg_ms=latency_avg_ms,
            token_count=token_count,
            robustness_rate=robustness_rate,
        )


def statistics_mean(values: list[float]) -> float:
    """计算平均值（避免 import statistics 命名冲突）。"""
    if not values:
        return 0.0
    return sum(values) / len(values)
