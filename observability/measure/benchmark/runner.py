# date: 2026-07-07
# dev: myf
# changelog: H5.3 新建性能基准测试——BenchmarkCase + BenchmarkSuite + BenchmarkRunner
"""性能基准测试 —— 可复现的基准测试套件与执行器。

本模块实现 :class:`BenchmarkCase` / :class:`BenchmarkSuite` / :class:`BenchmarkRunner`，
对 Agent 编排链路进行性能基准测试，采集延迟 / 吞吐 / 成功率指标。

设计要点：
    - **BenchmarkCase**：单个基准用例，含 ``name`` / ``func`` / ``setup`` / ``teardown``。
    - **BenchmarkSuite**：用例集合，可批量执行并汇总结果。
    - **BenchmarkRunner**：执行引擎，支持重复运行（``iterations``）取统计值。
    - **BenchmarkReport**：结果报告，含每用例的 min/avg/max/p99 延迟与成功率。

与现有架构的关系：
    - 实现 :class:`observability.api.BenchmarkAPI` Protocol。
    - 基准用例可调用 :class:`CyberOrchestrator` 的红蓝紫链。
    - 结果供 :mod:`observability.measure.evaluation` 评测消费。
"""

from __future__ import annotations

import contextlib
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


def _asdict(obj):
    return obj.model_dump() if isinstance(obj, BaseModel) else obj


@dataclass
class CaseResult:
    """单个基准用例的单次运行结果。

    Attributes:
        case_name: 用例名。
        iteration: 迭代号（第几次运行）。
        duration_ms: 耗时（毫秒）。
        success: 是否成功。
        output: 用例输出（可选）。
        error: 失败时的错误信息。
    """

    case_name: str
    iteration: int = 0
    duration_ms: float = 0.0
    success: bool = True
    output: Any = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_name": self.case_name,
            "iteration": self.iteration,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class CaseStats:
    """单个用例的统计汇总（多次运行后）。

    Attributes:
        case_name: 用例名。
        iterations: 总运行次数。
        success_count: 成功次数。
        failure_count: 失败次数。
        success_rate: 成功率（0.0-1.0）。
        latency_min_ms: 最小延迟。
        latency_avg_ms: 平均延迟。
        latency_max_ms: 最大延迟。
        latency_p99_ms: P99 延迟。
        latency_std_ms: 延迟标准差。
    """

    case_name: str = ""
    iterations: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    latency_min_ms: float = 0.0
    latency_avg_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_std_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class BenchmarkReport:
    """基准测试报告 —— 整个 suite 的汇总结果。

    Attributes:
        suite_id: 套件 ID。
        started_at: 开始时间戳。
        ended_at: 结束时间戳。
        total_duration_ms: 总耗时。
        case_stats: 每个用例的统计汇总。
        raw_results: 原始单次结果列表。
    """

    suite_id: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    total_duration_ms: float = 0.0
    case_stats: list[CaseStats] = field(default_factory=list)
    raw_results: list[CaseResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "case_stats": [s.to_dict() for s in self.case_stats],
            "raw_results": [r.to_dict() for r in self.raw_results],
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), default=str, ensure_ascii=False, indent=2)


@dataclass
class BenchmarkCase:
    """单个基准用例。

    Attributes:
        name: 用例名（如 ``"red_chain_basic"``）。
        func: 执行函数，签名 ``func() -> Any``，返回值记入 ``output``。
        setup: 可选的初始化函数，每次迭代前调用。
        teardown: 可选的清理函数，每次迭代后调用。
        description: 用例描述。
    """

    name: str
    func: Callable[[], Any]
    setup: Callable[[], None] | None = None
    teardown: Callable[[], None] | None = None
    description: str = ""


@dataclass
class BenchmarkSuite:
    """基准测试套件 —— 用例集合。

    Attributes:
        suite_id: 套件唯一标识。
        name: 套件可读名称。
        cases: 用例列表。
        iterations: 每个用例的重复运行次数（用于取统计值）。
    """

    suite_id: str
    name: str = ""
    cases: list[BenchmarkCase] = field(default_factory=list)
    iterations: int = 5

    def add_case(self, case: BenchmarkCase) -> None:
        """添加用例到套件。

        Args:
            case: 基准用例。
        """
        self.cases.append(case)


class BenchmarkRunner:
    """基准测试执行器 —— 运行 Suite 并生成 BenchmarkReport。

    实现 :class:`observability.api.BenchmarkAPI` Protocol。

    Attributes:
        _results: 历史报告（按 suite_id 索引）。
    """

    def __init__(self) -> None:
        """初始化执行器。"""
        self._results: dict[str, BenchmarkReport] = {}

    def run_suite(self, suite: BenchmarkSuite) -> BenchmarkReport:
        """执行一个基准测试套件。

        对每个用例运行 ``suite.iterations`` 次，采集延迟与成功率，
        汇总为 :class:`BenchmarkReport`。

        Args:
            suite: 要执行的基准测试套件。

        Returns:
            :class:`BenchmarkReport`，含每用例的统计汇总与原始结果。
        """
        report = BenchmarkReport(
            suite_id=suite.suite_id,
            started_at=time.time(),
        )
        for case in suite.cases:
            case_results: list[CaseResult] = []
            for i in range(suite.iterations):
                # setup
                if case.setup is not None:
                    try:
                        case.setup()
                    except Exception as e:  # noqa: BLE001
                        report.raw_results.append(
                            CaseResult(
                                case_name=case.name,
                                iteration=i,
                                success=False,
                                error=f"setup failed: {e!r}",
                            )
                        )
                        continue
                # 执行
                start = time.perf_counter()
                try:
                    output = case.func()
                    duration_ms = (time.perf_counter() - start) * 1000
                    result = CaseResult(
                        case_name=case.name,
                        iteration=i,
                        duration_ms=round(duration_ms, 2),
                        success=True,
                        output=output,
                    )
                except Exception as e:  # noqa: BLE001
                    duration_ms = (time.perf_counter() - start) * 1000
                    result = CaseResult(
                        case_name=case.name,
                        iteration=i,
                        duration_ms=round(duration_ms, 2),
                        success=False,
                        error=repr(e),
                    )
                case_results.append(result)
                report.raw_results.append(result)
                # teardown
                if case.teardown is not None:
                    with contextlib.suppress(Exception):
                        case.teardown()
                # teardown 失败不影响结果
            # 统计汇总
            stats = self._compute_stats(case.name, case_results)
            report.case_stats.append(stats)
        report.ended_at = time.time()
        report.total_duration_ms = round((report.ended_at - report.started_at) * 1000, 2)
        self._results[suite.suite_id] = report
        return report

    @staticmethod
    def _compute_stats(case_name: str, results: list[CaseResult]) -> CaseStats:
        """计算单个用例的统计汇总。

        Args:
            case_name: 用例名。
            results: 该用例的所有单次结果。

        Returns:
            :class:`CaseStats` 统计汇总。
        """
        if not results:
            return CaseStats(case_name=case_name)
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        durations = [r.duration_ms for r in results if r.success]
        # P99：当样本少时取最大值
        if len(durations) >= 100:
            p99 = statistics.quantiles(durations, n=100)[98]
        elif durations:
            p99 = max(durations)
        else:
            p99 = 0.0
        return CaseStats(
            case_name=case_name,
            iterations=len(results),
            success_count=success_count,
            failure_count=failure_count,
            success_rate=round(success_count / len(results), 4) if results else 0.0,
            latency_min_ms=round(min(durations), 2) if durations else 0.0,
            latency_avg_ms=round(statistics.mean(durations), 2) if durations else 0.0,
            latency_max_ms=round(max(durations), 2) if durations else 0.0,
            latency_p99_ms=round(p99, 2),
            latency_std_ms=round(statistics.stdev(durations), 2) if len(durations) >= 2 else 0.0,
        )

    def get_results(self, suite_id: str) -> dict[str, Any] | None:
        """获取历史报告（兼容 BenchmarkAPI）。

        Args:
            suite_id: 套件 ID。

        Returns:
            报告字典；不存在返回 None。
        """
        report = self._results.get(suite_id)
        return report.to_dict() if report else None
