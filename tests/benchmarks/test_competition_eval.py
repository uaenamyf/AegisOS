# date: 2026-09-14
# dev: AegisOS
# change: add regression tests for competition evidence evaluation
"""比赛证据评测测试：长程保持与异构路由。"""

from tooling.scripts.run_competition_eval import run_evaluation


def test_competition_evaluation_covers_long_horizon_and_routing():
    report = run_evaluation((5, 10))

    assert report["total_cases"] == 3
    assert report["passed_cases"] == 3
    assert report["pass_rate"] == 1.0
    assert [item["round_limit"] for item in report["long_horizon"]] == [5, 10]
    assert report["heterogeneous_routing"]["failure_fallback_tier"] == "edge"