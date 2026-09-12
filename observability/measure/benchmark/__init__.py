# date: 2026-07-07
# dev: myf
# changelog: H5.3 新建 benchmark 包——导出 BenchmarkCase/Suite/Runner/Report/CaseStats/CaseResult
"""性能基准测试包。

导出基准测试相关类型，供后端 benchmark router 与评测模块消费。
"""
from .runner import (
    BenchmarkCase,
    BenchmarkReport,
    BenchmarkRunner,
    BenchmarkSuite,
    CaseResult,
    CaseStats,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkSuite",
    "BenchmarkRunner",
    "BenchmarkReport",
    "CaseResult",
    "CaseStats",
]
