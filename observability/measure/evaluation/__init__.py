# date: 2026-07-07
# dev: myf
# changelog: H5.4 新建 evaluation 包——导出 Evaluator/EvaluationReport/DimensionScore/Metric + 5 评分函数
"""5 维度评测包。

导出 :class:`Evaluator` 及相关类型与评分函数，供后端 evaluation router 与前端评测面板消费。
"""
from .scorers import (
    DimensionScore,
    EvaluationReport,
    Evaluator,
    Metric,
    score_accuracy,
    score_latency,
    score_recall,
    score_resource,
    score_robustness,
)

__all__ = [
    "Evaluator",
    "EvaluationReport",
    "DimensionScore",
    "Metric",
    "score_accuracy",
    "score_recall",
    "score_latency",
    "score_resource",
    "score_robustness",
]
