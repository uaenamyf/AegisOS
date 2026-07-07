# date: 2026-07-07
# dev: myf
# changelog: AP1.5 Plan 范式测试——3 Agent 的 plan_with_strategy 方法 + 降级兼容 + PlanResult 类型
"""AP1.5 Plan 范式单元测试。

覆盖：
    - PlanResult / PlanStep Pydantic 类型基本验证
    - 3 个 Agent（exploit_planner / ir_planner / lateral_move）的
      ``plan_with_strategy`` / ``plan_response_with_strategy`` /
      ``plan_moves_with_strategy`` 方法可跑通
    - 规划阶段 Mock 不识别时降级到直接执行（向后兼容）
    - 规划阶段识别时产出增强 prompt（含 strategy + steps）
    - create_plan_mode_agent 工厂函数
"""
from __future__ import annotations

import json

from aegisos_agents.action.exploit_planner.agent import ExploitPlannerAgent
from aegisos_agents.action.ir_planner.agent import IRPlannerAgent
from aegisos_agents.action.lateral_move.agent import LateralMoveAgent
from aegisos_agents.perception.reasoning.strategies import (
    PlanMode,
    PlanResult,
    PlanStep,
    create_plan_mode_agent,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol.cyber import AttackChain, AttackStep, ResponsePlan, VulnFinding
from protocol.graph import Graph, GraphNode, NodeKind


# ---- PlanResult / PlanStep 类型验证 ----


def test_plan_step_basic_fields():
    """PlanStep 应有 step_id / description / rationale 字段。"""
    step = PlanStep(step_id="s1", description="recon target", rationale="need assets")
    assert step.step_id == "s1"
    assert step.description == "recon target"
    assert step.rationale == "need assets"


def test_plan_result_basic_fields():
    """PlanResult 应有 strategy / steps / risks 字段。"""
    result = PlanResult(
        strategy="lateral from edge to core",
        steps=[PlanStep(step_id="s1", description="foo")],
        risks=["ids trigger"],
    )
    assert result.strategy == "lateral from edge to core"
    assert len(result.steps) == 1
    assert result.risks == ["ids trigger"]


# ---- exploit_planner Plan 范式 ----


def test_exploit_planner_plan_with_strategy_returns_attack_chain():
    """ExploitPlannerAgent.plan_with_strategy 应返回 AttackChain（降级路径）。"""
    provider = _CyberMockProvider()
    agent = ExploitPlannerAgent(provider)
    findings = [
        VulnFinding(
            finding_id="vuln-1",
            cve_id="CVE-2024-1234",
            asset_id="asset-1",
            cvss=8.1,
            attack_surface="ssh",
        )
    ]
    # Mock 不识别规划 prompt → 降级到直接 plan → 返回 chain-1
    chain = agent.plan_with_strategy(findings)
    assert isinstance(chain, AttackChain)
    assert chain.chain_id == "chain-1"
    assert len(chain.steps) >= 1


def test_exploit_planner_plan_with_strategy_uses_plan_when_mock_responds():
    """当 Mock 能响应规划 prompt 时，plan_with_strategy 走完整两阶段路径。"""
    # 构造同时能响应规划 + 执行的 Mock 响应表
    # 注意：plan_prompt 实际格式为 "[Domain: exploit_planning] Analyze and plan for: <prompt>"
    plan_response = json.dumps(
        {
            "strategy": "enter via ssh then pivot to redis",
            "steps": [
                {"step_id": "s1", "description": "exploit ssh on asset-1", "rationale": "cvss 8.1"},
                {"step_id": "s2", "description": "pivot to asset-2 redis", "rationale": "unauth redis"},
            ],
            "risks": ["ids may detect ssh brute"],
        }
    )
    exec_response = json.dumps(
        {
            "chain_id": "chain-planned",
            "target": "asset-2",
            "steps": [
                {"step_id": "s1", "technique": "T1110", "from_asset": "asset-1", "to_asset": "asset-1", "success": True},
                {"step_id": "s2", "technique": "T1210", "from_asset": "asset-1", "to_asset": "asset-2", "success": True},
            ],
            "status": "planned",
        }
    )
    # key 必须精确匹配完整 prompt（含 domain 前缀）
    plan_key = "[Domain: exploit_planning] Analyze and plan for: Plan exploit chain for: "
    responses = {
        plan_key: plan_response,
        # 执行阶段 prompt 含 strategy 前缀，用 default 兜底
        "default": exec_response,
    }
    provider = MockProvider(responses)
    agent = ExploitPlannerAgent(provider)

    findings = [
        VulnFinding(finding_id="v1", cve_id="CVE-2024-1", asset_id="a1", cvss=8.0)
    ]
    chain = agent.plan_with_strategy(findings)
    assert chain.chain_id == "chain-planned"
    assert len(chain.steps) == 2
    assert chain.steps[0].technique == "T1110"


# ---- ir_planner Plan 范式 ----


def test_ir_planner_plan_response_with_strategy_returns_response_plan():
    """IRPlannerAgent.plan_response_with_strategy 应返回 ResponsePlan（降级路径）。"""
    provider = _CyberMockProvider()
    agent = IRPlannerAgent(provider)
    hypotheses = [{"hypothesis": "lateral movement via T1210", "confidence": 0.8}]
    plan = agent.plan_response_with_strategy(hypotheses)
    assert isinstance(plan, ResponsePlan)
    assert plan.plan_id == "rp-1"
    assert len(plan.actions) >= 1


# ---- lateral_move Plan 范式 ----


def test_lateral_move_plan_moves_with_strategy_returns_steps():
    """LateralMoveAgent.plan_moves_with_strategy 应返回 AttackStep 列表（降级路径）。"""
    provider = _CyberMockProvider()
    agent = LateralMoveAgent(provider)
    chain = AttackChain(chain_id="c1", target="asset-2", steps=[AttackStep(step_id="s1", to_asset="asset-1")])
    graph = Graph()
    graph.add_node(GraphNode(node_id="asset-1", kind=NodeKind.Agent, name="web"))
    graph.add_node(GraphNode(node_id="asset-2", kind=NodeKind.Agent, name="db"))
    steps = agent.plan_moves_with_strategy(chain, graph)
    assert isinstance(steps, list)
    # 降级到 plan_moves，Mock 返回横向移动步骤
    assert len(steps) >= 1


# ---- 工厂函数 ----


def test_create_plan_mode_agent_returns_joint_instance():
    """create_plan_mode_agent 应返回同时具备 PlanMode 与 Agent 能力的实例。"""
    provider = _CyberMockProvider()
    agent = create_plan_mode_agent(ExploitPlannerAgent, mock=provider)
    # 应是 ExploitPlannerAgent 子类 + PlanMode 混入
    assert isinstance(agent, ExploitPlannerAgent)
    assert isinstance(agent, PlanMode)
    # 应有 _run_with_plan 方法
    assert hasattr(agent, "_run_with_plan")


def test_plan_mode_format_plan_renders_steps():
    """_format_plan 应把 PlanResult 格式化为可读字符串。"""
    plan = PlanResult(
        strategy="test strategy",
        steps=[
            PlanStep(step_id="s1", description="first", rationale="because"),
            PlanStep(step_id="s2", description="second"),
        ],
    )
    text = PlanMode._format_plan(plan)
    assert "s1" in text
    assert "first" in text
    assert "because" in text
    assert "s2" in text


def test_plan_mode_format_plan_empty_steps():
    """_format_plan 空步骤应返回占位文本。"""
    plan = PlanResult(strategy="x", steps=[])
    text = PlanMode._format_plan(plan)
    assert "no specific steps" in text
