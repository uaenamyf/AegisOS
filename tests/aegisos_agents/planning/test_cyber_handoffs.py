# date: 2026-07-08
# dev: myf
"""R4.2: SDK Agent.handoffs 声明式链测试。

验证：
    - ``run_red_chain_via_handoffs`` / ``run_blue_chain_via_handoffs`` 方法存在
    - Mock 模式下回退到手动链（MockSDKModel 不产生工具调用）
    - ``ChainContext`` 正确累积各步产出
    - handoff 回调正确捕获中间产出
"""
from __future__ import annotations

from aegisos_agents.planning.orchestrator import ChainContext, CyberOrchestrator
from aegisos_agents.planning.orchestrator.cyber_orchestrator import _SDK_HANDOFF_AVAILABLE
from backend.mocks.cyber_provider import _CyberMockProvider


def test_chain_context_defaults():
    """ChainContext 默认值应为 None / 空列表。"""
    ctx = ChainContext()
    assert ctx.target_range is None
    assert ctx.event_stream == []
    assert ctx.recon_output is None
    assert ctx.vuln_output is None
    assert ctx.exploit_output is None
    assert ctx.detector_output is None
    assert ctx.triage_output is None
    assert ctx.hunt_output is None
    assert ctx.ir_output is None
    assert ctx.chain is None
    assert ctx.plan is None


def test_chain_context_with_target_range():
    """ChainContext 可带初始数据构造。"""
    ctx = ChainContext(target_range="10.0.0.0/24")
    assert ctx.target_range == "10.0.0.0/24"


def test_red_chain_via_handoffs_falls_back_in_mock_mode():
    """Mock 模式下 run_red_chain_via_handoffs 应回退到 run_red_chain。

    MockSDKModel 返回纯文本（非工具调用），LLM 不会触发 handoff，
    因此 handoff 链应回退到手动链。
    """
    orch = CyberOrchestrator(mock=_CyberMockProvider())

    result = orch.run_red_chain_via_handoffs("10.0.0.0/24")

    # 回退后应与手动链产出结构一致
    assert "assets" in result
    assert "findings" in result
    assert "chain" in result
    assert len(result["assets"]) >= 2
    assert len(result["findings"]) >= 1
    assert result["chain"].chain_id == "chain-1"


def test_blue_chain_via_handoffs_falls_back_in_mock_mode():
    """Mock 模式下 run_blue_chain_via_handoffs 应回退到 run_blue_chain。"""
    orch = CyberOrchestrator(mock=_CyberMockProvider())
    events = [{"event": "ssh-brute-force", "src": "10.0.0.99", "dst": "10.0.0.5"}]

    result = orch.run_blue_chain_via_handoffs(events)

    assert "alerts" in result
    assert "triaged" in result
    assert "hypotheses" in result
    assert "plan" in result
    assert len(result["alerts"]) >= 1
    assert result["plan"].plan_id == "rp-1"


def test_context_to_red_result():
    """_context_to_red_result 应将 ChainContext 转换为结果字典。"""
    orch = CyberOrchestrator(mock=_CyberMockProvider())
    ctx = ChainContext(
        target_range="10.0.0.0/24",
        recon_output={
            "assets": [
                {"asset_id": "a-1", "host": "10.0.0.1", "services": ["ssh"], "os": "linux"},
            ]
        },
        vuln_output={
            "findings": [
                {"finding_id": "f-1", "cve_id": "CVE-2024-1234", "asset_id": "a-1", "cvss": 7.5},
            ]
        },
        exploit_output={
            "chain_id": "chain-1",
            "target": "10.0.0.0/24",
            "steps": [
                {"step_id": "s-1", "technique": "T1110", "from_asset": "a-1", "to_asset": "a-2", "success": True},
            ],
            "status": "planned",
        },
    )
    ctx.chain = "placeholder"  # 标记为已完成

    result = orch._context_to_red_result(ctx)

    assert len(result["assets"]) == 1
    assert result["assets"][0].asset_id == "a-1"
    assert len(result["findings"]) == 1
    assert result["findings"][0].cve_id == "CVE-2024-1234"
    assert result["chain"].chain_id == "chain-1"
    assert len(result["chain"].steps) == 1


def test_context_to_blue_result():
    """_context_to_blue_result 应将 ChainContext 转换为结果字典。"""
    orch = CyberOrchestrator(mock=_CyberMockProvider())
    ctx = ChainContext(
        detector_output={
            "alerts": [
                {"alert_id": "al-1", "severity": "high", "src": "10.0.0.99", "dst": "10.0.0.5", "technique": "T1110"},
            ]
        },
        triage_output={
            "alerts": [
                {"alert_id": "al-1", "severity": "critical", "src": "10.0.0.99", "dst": "10.0.0.5", "technique": "T1110"},
            ]
        },
        hunt_output={"hypotheses": [{"h": "lateral movement detected"}]},
        ir_output={
            "plan_id": "rp-1",
            "actions": [{"action_id": "a-1", "kind": "block", "target": "10.0.0.99"}],
            "confidence": 0.9,
            "rollback": {"steps": ["unblock"]},
        },
    )
    ctx.plan = "placeholder"  # 标记为已完成

    result = orch._context_to_blue_result(ctx)

    assert len(result["alerts"]) == 1
    assert result["alerts"][0].alert_id == "al-1"
    assert len(result["triaged"]) == 1
    assert result["triaged"][0].severity == "critical"
    assert len(result["hypotheses"]) == 1
    assert result["plan"].plan_id == "rp-1"
    assert result["plan"].confidence == 0.9


def test_sdk_handoff_available():
    """SDK handoff 模块应可用（openai-agents SDK 已安装）。"""
    assert _SDK_HANDOFF_AVAILABLE is True


def test_configure_red_handoff_callbacks():
    """_configure_red_handoff_callbacks 应设置 handoff 链。"""
    if not _SDK_HANDOFF_AVAILABLE:
        return

    from agents import Agent as SDKAgent

    orch = CyberOrchestrator(mock=_CyberMockProvider())
    ctx = ChainContext()

    recon = SDKAgent(name="recon", instructions="test")
    vuln = SDKAgent(name="vuln", instructions="test")
    exploit = SDKAgent(name="exploit", instructions="test")

    orch._configure_red_handoff_callbacks(ctx, recon, vuln, exploit)

    # 验证 handoffs 已配置
    assert len(recon.handoffs) == 1
    assert len(vuln.handoffs) == 1


def test_configure_blue_handoff_callbacks():
    """_configure_blue_handoff_callbacks 应设置 handoff 链。"""
    if not _SDK_HANDOFF_AVAILABLE:
        return

    from agents import Agent as SDKAgent

    orch = CyberOrchestrator(mock=_CyberMockProvider())
    ctx = ChainContext()

    detector = SDKAgent(name="detector", instructions="test")
    triage = SDKAgent(name="triage", instructions="test")
    hunt = SDKAgent(name="hunt", instructions="test")
    ir = SDKAgent(name="ir", instructions="test")

    orch._configure_blue_handoff_callbacks(ctx, detector, triage, hunt, ir)

    assert len(detector.handoffs) == 1
    assert len(triage.handoffs) == 1
    assert len(hunt.handoffs) == 1
