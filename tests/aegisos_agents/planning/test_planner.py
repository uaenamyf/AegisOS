# date: 2026-07-06
# dev: myf
# changelog: Planner 单元测试——红/蓝/紫场景分解 + 默认场景 + 未知场景报错
"""Planner 单元测试。

覆盖：红队链式分解、蓝队链式分解、紫队并行分解、默认 generic 场景、
未知场景报错、DAG 与 Task 列表一致性。
"""
from __future__ import annotations

from protocol.scheduler import Plan, Task, TaskStatus

from aegisos_agents.planning.planner import Planner


def test_plan_cyber_red_chain():
    """红队场景应分解为 4 个链式子任务。"""
    planner = Planner()
    plan = planner.plan("对 10.0.0.0/24 攻击", scenario="cyber_red")

    assert isinstance(plan, Plan)
    assert plan.goal == "对 10.0.0.0/24 攻击"
    assert len(plan.tasks) == 4
    assert list(plan.dag.keys()) == [
        "recon", "vuln_correlator", "exploit_planner", "lateral_move",
    ]
    # 链式依赖：recon 无依赖，vuln_correlator 依赖 recon，...
    assert plan.dag["recon"] == []
    assert plan.dag["vuln_correlator"] == ["recon"]
    assert plan.dag["exploit_planner"] == ["vuln_correlator"]
    assert plan.dag["lateral_move"] == ["exploit_planner"]
    # 每个 task 的 dependency 应与 dag 一致
    assert plan.tasks[0].dependency == []
    assert plan.tasks[1].dependency == [plan.tasks[0].task_id]
    assert all(t.status == TaskStatus.Pending for t in plan.tasks)


def test_plan_cyber_blue_chain():
    """蓝队场景应分解为 4 个链式子任务（detector → ir_planner）。"""
    planner = Planner()
    plan = planner.plan("防御检测", scenario="cyber_blue")

    assert list(plan.dag.keys()) == [
        "detector", "triage", "threat_hunt", "ir_planner",
    ]
    assert plan.dag["detector"] == []
    assert plan.dag["ir_planner"] == ["threat_hunt"]
    assert len(plan.tasks) == 4


def test_plan_cyber_purple_parallel():
    """紫队场景应分解为 2 个并行子任务（critic 与 reviewer 均无依赖）。"""
    planner = Planner()
    plan = planner.plan("紫队校验", scenario="cyber_purple")

    assert list(plan.dag.keys()) == ["critic", "reviewer"]
    # 并行：两者均无前驱
    assert plan.dag["critic"] == []
    assert plan.dag["reviewer"] == []
    assert len(plan.tasks) == 2
    assert plan.tasks[0].dependency == []
    assert plan.tasks[1].dependency == []


def test_plan_generic_default():
    """未指定 scenario 时使用默认 generic 模板。"""
    planner = Planner(default_scenario="generic")
    plan = planner.plan("通用任务")

    assert list(plan.dag.keys()) == ["analyze", "execute", "verify"]
    assert plan.dag["analyze"] == []
    assert plan.dag["execute"] == ["analyze"]
    assert plan.dag["verify"] == ["execute"]
    # goal 应包含父目标
    assert "通用任务" in plan.tasks[0].goal


def test_plan_unknown_scenario_raises():
    """未知场景应抛 ValueError。"""
    planner = Planner()
    import pytest

    with pytest.raises(ValueError, match="Unknown scenario"):
        planner.plan("x", scenario="nonexistent")


def test_plan_task_ids_unique():
    """同一 Plan 内所有 task_id 应唯一。"""
    planner = Planner()
    plan = planner.plan("test", scenario="cyber_red")

    ids = [t.task_id for t in plan.tasks]
    assert len(ids) == len(set(ids))


def test_available_scenarios():
    """available_scenarios 应返回全部模板名。"""
    planner = Planner()
    scenes = planner.available_scenarios()
    assert set(scenes) == {"cyber_red", "cyber_blue", "cyber_purple", "generic"}
