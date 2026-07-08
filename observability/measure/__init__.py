# date: 2026-07-07
# dev: myf
# changelog: H5.4 新建 measure 包——导出 benchmark + evaluation 子包
"""度量包 —— 基准测试 + 评估评分。

聚合 :mod:`observability.measure.benchmark` 与 :mod:`observability.measure.evaluation`。
"""
from observability.measure.benchmark import (
    BenchmarkCase,
    BenchmarkReport,
    BenchmarkRunner,
    BenchmarkSuite,
)
from observability.measure.evaluation import (
    DimensionScore,
    EvaluationReport,
    Evaluator,
    Metric,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkSuite",
    "BenchmarkRunner",
    "BenchmarkReport",
    "Evaluator",
    "EvaluationReport",
    "DimensionScore",
    "Metric",
]
