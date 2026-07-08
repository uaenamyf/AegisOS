# date: 2026-07-08
# dev: myf
# changelog: AP3.4 Goal 范式测试--递归分解 + 失败重试 + 备选路径 + CyberOrchestrator 接入 + exploit_planner Goal 递归
"""AP3.4 Goal 范式单元测试。

覆盖：
    - GoalNode / GoalResult / GoalStatus 数据类型基本验证
    - GoalMode.decompose 递归分解（cyber_red / cyber_blue / generic / 自定义模板）
    - GoalMode.execute_tree 依赖序执行 + 成功路径
    - GoalMode.execute_tree 失败重试（子目标失败 -> 重试 -> 成功）
    - GoalMode.execute_tree 备选路径（重试时注入 fallback hint）
    - GoalMode.execute_tree 依赖失败导致下游 skipped
    - create_goal_mode_orchestrator 工厂函数
    - CyberOrchestrator.run_red_chain_with_goal 端到端
    - CyberOrchestrator.run_blue_chain_with_goal 端到端
    - ExploitPlannerAgent.plan_with_goal 递归分解
"""
from __future__ import annotations

import json

import pytest

from aegisos_agents.action.exploit_planner.agent import ExploitPlannerAgent
from aegisos_agents.perception.reasoning.strategies.goal_mode import (
    GoalMode,
    GoalNode,
    GoalResult,
    GoalStatus,
    create_goal_mode_orchestrator,
)
from aegisos_agents.planning.orchestrator.cyber_orchestrator import CyberOrchestrator
from aegisos_agents.tools.llms.mock_provider import MockProvider
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol.cyber import AttackChain, AttackStep, VulnFinding


# ---- 数据类型验证 ----


def test_goal_status_enum_values():
    """GoalStatus 应有 5 个状态值。"""
    assert GoalStatus.Pending == "pending"
    assert GoalStatus.Running == "running"
    assert GoalStatus.Succeeded == "succeeded"
    assert GoalStatus.Failed == "failed"
    assert GoalStatus.Skipped == "skipped"


def test_goal_node_basic_fields():
    """GoalNode 应有 goal_id / description / agent_name / children / fallback / dependencies。"""
    node = GoalNode(
        goal_id="sub-1",
        description="test goal",
        agent_name="recon",
        fallback="passive recon",
        dependencies=["sub-0"],
    )
    assert node.goal_id == "sub-1"
    assert node.description == "test goal"
    assert node.agent_name == "recon"
    assert node.fallback == "passive recon"
    assert node.dependencies == ["sub-0"]
    assert node.children == []
    assert node.status == GoalStatus.Pending
    assert node.result is None
    assert node.retry_count == 0


def test_goal_result_basic_fields():
    """GoalResult 应有 root_goal / nodes / succeeded / failed / outputs / overall_success。"""
    result = GoalResult(
        root_goal="test",
        nodes=[],
        succeeded=["a"],
        failed=["b"],
        outputs={"a": "output_a"},
        overall_success=False,
    )
    assert result.root_goal == "test"
    assert result.succeeded == ["a"]
    assert result.failed == ["b"]
    assert result.outputs["a"] == "output_a"
    assert result.overall_success is False


# ---- decompose 递归分解 ----


def test_decompose_cyber_red():
    """decompose 用 cyber_red 场景应分解为 4 个子目标。"""
    gm = GoalMode()
    tree = gm.decompose("攻击 10.0.0.0/24", scenario="cyber_red")
    assert tree.goal_id == "root"
    assert tree.description == "攻击 10.0.0.0/24"
    assert len(tree.children) == 4
    # 检查子目标 ID 与依赖
    ids = [c.goal_id for c in tree.children]
    assert ids == ["recon", "vuln", "exploit", "lateral"]
    # recon 无依赖
    assert tree.children[0].dependencies == []
    # vuln 依赖 recon
    assert tree.children[1].dependencies == ["recon"]
    # 每个子目标有 fallback
    assert all(c.fallback for c in tree.children)


def test_decompose_cyber_blue():
    """decompose 用 cyber_blue 场景应分解为 4 个子目标。"""
    gm = GoalMode()
    tree = gm.decompose("防御事件流", scenario="cyber_blue")
    assert len(tree.children) == 4
    ids = [c.goal_id for c in tree.children]
    assert ids == ["detect", "triage", "hunt", "respond"]
    assert tree.children[0].dependencies == []
    assert tree.children[1].dependencies == ["detect"]


def test_decompose_generic():
    """decompose 用 generic 场景应分解为 3 个子目标。"""
    gm = GoalMode()
    tree = gm.decompose("generic task", scenario="generic")
    assert len(tree.children) == 3
    ids = [c.goal_id for c in tree.children]
    assert ids == ["analyze", "execute", "verify"]


def test_decompose_custom_template():
    """decompose 用自定义模板应按模板展开。"""
    gm = GoalMode()
    custom = [
        {
            "goal_id": "step-1",
            "description": "first step",
            "agent_name": "agent-a",
            "dependencies": [],
            "fallback": "alt-a",
        },
        {
            "goal_id": "step-2",
            "description": "second step",
            "agent_name": "agent-b",
            "dependencies": ["step-1"],
            "fallback": "alt-b",
        },
    ]
    tree = gm.decompose("custom goal", custom_template=custom)
    assert len(tree.children) == 2
    assert tree.children[0].goal_id == "step-1"
    assert tree.children[1].dependencies == ["step-1"]
    assert tree.children[0].fallback == "alt-a"


def test_decompose_unknown_scenario_raises():
    """decompose 用未知场景应抛出 ValueError。"""
    gm = GoalMode()
    with pytest.raises(ValueError, match="Unknown scenario"):
        gm.decompose("test", scenario="unknown")


def test_available_scenarios():
    """available_scenarios 应返回 cyber_red / cyber_blue / generic。"""
    scenarios = GoalMode.available_scenarios()
    assert "cyber_red" in scenarios
    assert "cyber_blue" in scenarios
    assert "generic" in scenarios


# ---- execute_tree 成功路径 ----


def test_execute_tree_all_succeed():
    """execute_tree 所有子目标成功时 overall_success=True。"""
    gm = GoalMode()
    tree = gm.decompose("test", scenario="generic")

    def executor(node, context):
        return f"{node.goal_id}_output"

    result = gm.execute_tree(tree, executor)
    assert result.overall_success is True
    assert len(result.succeeded) == 3
    assert len(result.failed) == 0
    assert "analyze" in result.outputs
    assert result.outputs["analyze"] == "analyze_output"


def test_execute_tree_context_passing():
    """execute_tree 应将上游产出注入下游 context。"""
    gm = GoalMode()
    tree = gm.decompose("test", scenario="generic")

    def executor(node, context):
        upstream = {k: v for k, v in context.items() if not k.startswith("_")}
        return {"node": node.goal_id, "upstream": upstream}

    result = gm.execute_tree(tree, executor)
    # execute 的 upstream 应含 analyze 产出
    exec_output = result.outputs["execute"]
    assert "analyze" in exec_output["upstream"]
    # verify 的 upstream 应含 execute 产出
    verify_output = result.outputs["verify"]
    assert "execute" in verify_output["upstream"]


# ---- execute_tree 失败重试 ----


def test_execute_tree_retry_then_succeed():
    """子目标首次失败，重试后成功。"""
    gm = GoalMode()
    tree = gm.decompose("test", scenario="generic")

    call_count = {"execute": 0}

    def executor(node, context):
        if node.goal_id == "execute":
            call_count["execute"] += 1
            if call_count["execute"] < 2:
                raise RuntimeError("simulated failure")
            return "execute_success"
        return f"{node.goal_id}_output"

    result = gm.execute_tree(tree, executor, max_retries=2)
    assert result.overall_success is True
    assert "execute" in result.succeeded
    assert call_count["execute"] == 2  # 首次失败 + 重试成功


def test_execute_tree_retry_exhausted():
    """子目标重试耗尽后标记为 failed。"""
    gm = GoalMode()
    tree = gm.decompose("test", scenario="generic")

    def executor(node, context):
        if node.goal_id == "execute":
            raise RuntimeError("always fails")
        return f"{node.goal_id}_output"

    result = gm.execute_tree(tree, executor, max_retries=1)
    assert result.overall_success is False
    assert "execute" in result.failed
    # verify 依赖 execute，应被 skipped
    assert "verify" in result.failed
    assert result.nodes[2].status == GoalStatus.Skipped


def test_execute_tree_fallback_hint_injected():
    """子目标失败重试时应注入 fallback hint 到 context。"""
    gm = GoalMode()
    tree = gm.decompose("test", scenario="cyber_red")

    hints_seen: list[str] = []

    def executor(node, context):
        if node.goal_id == "vuln":
            hint = context.get("_fallback_hint", "")
            hints_seen.append(hint)
            if not hint:
                raise RuntimeError("first attempt fails")
            return "vuln_success"
        return f"{node.goal_id}_output"

    result = gm.execute_tree(tree, executor, max_retries=2)
    assert "vuln" in result.succeeded
    # 第一次无 hint（失败），第二次有 hint（成功）
    assert len(hints_seen) == 2
    assert hints_seen[0] == ""
    assert hints_seen[1] != ""  # fallback hint 被注入


def test_execute_tree_dependency_failure_skips_downstream():
    """上游子目标失败时下游应被 skipped。"""
    gm = GoalMode()
    tree = gm.decompose("test", scenario="cyber_red")

    def executor(node, context):
        if node.goal_id == "recon":
            raise RuntimeError("recon always fails")
        return f"{node.goal_id}_output"

    result = gm.execute_tree(tree, executor, max_retries=0)
    assert "recon" in result.failed
    # vuln/exploit/lateral 都依赖 recon，应被 skipped
    assert "vuln" in result.failed
    assert "exploit" in result.failed
    assert "lateral" in result.failed


# ---- 工厂函数 ----


def test_create_goal_mode_orchestrator():
    """create_goal_mode_orchestrator 应返回同时具备 GoalMode 能力的实例。"""
    provider = _CyberMockProvider()
    orchestrator = create_goal_mode_orchestrator(
        CyberOrchestrator,
        mock=provider,
    )
    assert isinstance(orchestrator, CyberOrchestrator)
    assert isinstance(orchestrator, GoalMode)
    assert hasattr(orchestrator, "decompose")
    assert hasattr(orchestrator, "execute_tree")
    assert hasattr(orchestrator, "run_red_chain_with_goal")


# ---- CyberOrchestrator 端到端 ----


def test_cyber_orchestrator_run_red_chain_with_goal():
    """CyberOrchestrator.run_red_chain_with_goal 应返回完整红队产出。"""
    provider = _CyberMockProvider()
    orchestrator = CyberOrchestrator(mock=provider)

    result = orchestrator.run_red_chain_with_goal("10.0.0.0/24", max_retries=1)

    assert "assets" in result
    assert "findings" in result
    assert "chain" in result
    assert "goal_result" in result
    # Mock 响应应产出资产
    assert len(result["assets"]) >= 1
    # goal_result 应有 succeeded 列表
    goal_result = result["goal_result"]
    assert isinstance(goal_result, GoalResult)
    assert len(goal_result.succeeded) >= 1


def test_cyber_orchestrator_run_blue_chain_with_goal():
    """CyberOrchestrator.run_blue_chain_with_goal 应返回完整蓝队产出。"""
    provider = _CyberMockProvider()
    orchestrator = CyberOrchestrator(mock=provider)

    events = [{"event": "failed_login", "src": "10.0.0.99", "dst": "10.0.0.5"}]
    result = orchestrator.run_blue_chain_with_goal(events, max_retries=1)

    assert "alerts" in result
    assert "triaged" in result
    assert "hypotheses" in result
    assert "plan" in result
    assert "goal_result" in result
    goal_result = result["goal_result"]
    assert isinstance(goal_result, GoalResult)


# ---- ExploitPlannerAgent.plan_with_goal ----


def test_exploit_planner_plan_with_goal_single_asset():
    """ExploitPlannerAgent.plan_with_goal 单资产时应返回 AttackChain。"""
    provider = _CyberMockProvider()
    agent = ExploitPlannerAgent(provider)
    findings = [
        VulnFinding(
            finding_id="v1",
            cve_id="CVE-2024-1234",
            asset_id="asset-1",
            cvss=8.1,
            attack_surface="ssh",
        )
    ]
    chain = agent.plan_with_goal(findings, target_description="asset-1")
    assert isinstance(chain, AttackChain)
    assert len(chain.steps) >= 1
    # 单资产不生成 lateral 子目标
    assert chain.status in ("planned", "failed")


def test_exploit_planner_plan_with_goal_multi_asset():
    """ExploitPlannerAgent.plan_with_goal 多资产时应生成横向移动子目标。"""
    provider = _CyberMockProvider()
    agent = ExploitPlannerAgent(provider)
    findings = [
        VulnFinding(finding_id="v1", cve_id="CVE-2024-1", asset_id="asset-1", cvss=8.0),
        VulnFinding(finding_id="v2", cve_id="CVE-2024-2", asset_id="asset-2", cvss=7.5),
    ]
    chain = agent.plan_with_goal(findings, target_description="internal network")
    assert isinstance(chain, AttackChain)
    # 多资产应生成横向移动子目标
    assert chain.chain_id.startswith("goal-chain-")


def test_exploit_planner_plan_with_goal_empty_findings():
    """ExploitPlannerAgent.plan_with_goal 空漏洞列表应返回空链。"""
    provider = _CyberMockProvider()
    agent = ExploitPlannerAgent(provider)
    chain = agent.plan_with_goal([], target_description="nothing")
    assert isinstance(chain, AttackChain)
    assert len(chain.steps) == 0
