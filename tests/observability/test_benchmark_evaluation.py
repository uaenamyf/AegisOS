# date: 2026-07-07
# dev: myf
# changelog: H5.3/H5.4 Benchmark + Evaluation 单元测试
"""H5.3 基准测试 + H5.4 5 维度评测单元测试。"""
from __future__ import annotations

from observability.measure.benchmark import (
    BenchmarkCase,
    BenchmarkRunner,
    BenchmarkSuite,
)
from observability.measure.evaluation import (
    Evaluator,
    score_accuracy,
    score_latency,
    score_recall,
    score_resource,
    score_robustness,
)

# ---- H5.3 Benchmark ----


def test_benchmark_runner_executes_case():
    """执行器应运行用例并采集延迟。"""
    case = BenchmarkCase(name="test_case", func=lambda: 1 + 1)
    suite = BenchmarkSuite(suite_id="s1", name="test", cases=[case], iterations=3)
    runner = BenchmarkRunner()

    report = runner.run_suite(suite)

    assert report.suite_id == "s1"
    assert len(report.case_stats) == 1
    stats = report.case_stats[0]
    assert stats.case_name == "test_case"
    assert stats.iterations == 3
    assert stats.success_count == 3
    assert stats.success_rate == 1.0
    assert stats.latency_avg_ms >= 0  # 空函数可能测得 0ms


def test_benchmark_captures_failure():
    """用例抛异常应记为失败。"""
    def _fail():
        raise RuntimeError("boom")

    case = BenchmarkCase(name="fail_case", func=_fail)
    suite = BenchmarkSuite(suite_id="s2", cases=[case], iterations=2)
    runner = BenchmarkRunner()

    report = runner.run_suite(suite)

    stats = report.case_stats[0]
    assert stats.failure_count == 2
    assert stats.success_count == 0
    assert stats.success_rate == 0.0


def test_benchmark_setup_teardown_called():
    """setup/teardown 应在每次迭代前后调用。"""
    counter = {"setup": 0, "teardown": 0}

    def _setup():
        counter["setup"] += 1

    def _teardown():
        counter["teardown"] += 1

    case = BenchmarkCase(
        name="c", func=lambda: None, setup=_setup, teardown=_teardown
    )
    suite = BenchmarkSuite(suite_id="s3", cases=[case], iterations=3)
    BenchmarkRunner().run_suite(suite)

    assert counter["setup"] == 3
    assert counter["teardown"] == 3


def test_benchmark_get_results():
    """get_results 应返回历史报告字典。"""
    suite = BenchmarkSuite(
        suite_id="s4", cases=[BenchmarkCase(name="c", func=lambda: None)], iterations=1
    )
    runner = BenchmarkRunner()
    runner.run_suite(suite)
    result = runner.get_results("s4")
    assert result is not None
    assert result["suite_id"] == "s4"


def test_benchmark_report_to_json():
    """报告应可序列化为 JSON。"""
    suite = BenchmarkSuite(
        suite_id="s5", cases=[BenchmarkCase(name="c", func=lambda: 42)], iterations=2
    )
    report = BenchmarkRunner().run_suite(suite)
    json_str = report.to_json()
    assert '"suite_id": "s5"' in json_str


# ---- H5.4 Evaluation 评分函数 ----


def test_score_accuracy_full():
    """准确率 1.0 应得满分。"""
    assert score_accuracy(1.0) == 100.0


def test_score_accuracy_half():
    """准确率 0.5 应得 50 分。"""
    assert score_accuracy(0.5) == 50.0


def test_score_latency_low():
    """低延迟应得高分。"""
    assert score_latency(100.0, target_ms=5000.0) == 100.0


def test_score_latency_high():
    """高延迟应得低分。"""
    score = score_latency(10000.0, target_ms=5000.0)
    assert score == 50.0


def test_score_recall():
    """召回率评分。"""
    assert score_recall(0.8, target=0.8) == 100.0
    assert score_recall(0.4, target=0.8) == 50.0


def test_score_resource():
    """资源评分。"""
    assert score_resource(5000, target=10000) == 100.0
    assert score_resource(20000, target=10000) == 50.0


def test_score_robustness():
    """鲁棒性评分。"""
    assert score_robustness(0.9, target=0.9) == 100.0
    assert score_robustness(0.45, target=0.9) == 50.0


# ---- H5.4 Evaluator ----


def test_evaluator_produces_5_dimensions():
    """Evaluator.evaluate 应产出 5 个维度。"""
    evaluator = Evaluator()
    report = evaluator.evaluate(
        run_id="r1",
        accuracy=0.9,
        recall=0.8,
        latency_avg_ms=2000,
        token_count=5000,
        robustness_rate=0.95,
    )
    assert len(report.dimensions) == 5
    dims = {d.dimension for d in report.dimensions}
    assert dims == {"accuracy", "recall", "latency", "resource", "robustness"}
    assert report.total_score > 0
    assert report.total_score <= 100


def test_evaluator_perfect_scores():
    """全满分指标应得总分 100。"""
    evaluator = Evaluator()
    report = evaluator.evaluate(
        run_id="r2",
        accuracy=1.0,
        recall=1.0,
        latency_avg_ms=100,
        token_count=100,
        robustness_rate=1.0,
    )
    assert report.total_score == 100.0


def test_evaluator_get_report():
    """get_report 应返回历史报告。"""
    evaluator = Evaluator()
    evaluator.evaluate(run_id="r3", accuracy=0.5)
    report = evaluator.get_report("r3")
    assert report is not None
    assert report["run_id"] == "r3"


def test_evaluator_from_benchmark():
    """evaluate_from_benchmark 应从基准报告提取延迟。"""
    # 构造一个简单的 benchmark report
    case = BenchmarkCase(name="c", func=lambda: None)
    suite = BenchmarkSuite(suite_id="sb", cases=[case], iterations=2)
    bench_report = BenchmarkRunner().run_suite(suite)

    evaluator = Evaluator()
    report = evaluator.evaluate_from_benchmark(
        run_id="r4",
        benchmark_report=bench_report,
        accuracy=0.9,
        recall=0.8,
    )
    assert len(report.dimensions) == 5
    # 延迟维度应从 benchmark 提取
    lat_dim = report.dimension_map["latency"]
    assert lat_dim.metrics[0].name == "latency_avg_ms"
    assert lat_dim.metrics[0].value >= 0  # 空函数可能测得 0ms


def test_evaluation_report_to_json():
    """评测报告应可序列化为 JSON。"""
    evaluator = Evaluator()
    report = evaluator.evaluate(run_id="r5", accuracy=0.8)
    json_str = report.to_json()
    assert '"run_id": "r5"' in json_str
    assert '"total_score"' in json_str
