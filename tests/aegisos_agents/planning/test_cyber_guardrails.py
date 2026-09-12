# date: 2026-07-08
# dev: myf
"""R4.3: SDK output_guardrails 紫队校验测试。

验证：
    - ``create_attack_chain_guardrail()`` 返回有效的 ``OutputGuardrail``
    - ``run_red_chain_with_guardrail`` 正常执行并返回结果
    - guardrail 通过时 ``guardrail_passed=True``
    - mock 模式下 guardrail 校验通过（MockSDKModel 返回有效 JSON）
"""
from __future__ import annotations

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from aegisos_agents.planning.orchestrator.cyber_orchestrator import _SDK_GUARDRAIL_AVAILABLE
from backend.mocks.cyber_provider import _CyberMockProvider


def test_create_attack_chain_guardrail():
    """create_attack_chain_guardrail 应返回 OutputGuardrail 实例。"""
    if not _SDK_GUARDRAIL_AVAILABLE:
        return

    guardrail = CyberOrchestrator.create_attack_chain_guardrail()

    assert guardrail is not None
    assert hasattr(guardrail, "guardrail_function")
    assert guardrail.get_name() == "attack_chain_validator"


def test_run_red_chain_with_guardrail_passes():
    """run_red_chain_with_guardrail 在 mock 模式下应正常通过。"""
    orch = CyberOrchestrator(mock=_CyberMockProvider())

    result = orch.run_red_chain_with_guardrail("10.0.0.0/24")

    assert "assets" in result
    assert "findings" in result
    assert "chain" in result
    assert "guardrail_passed" in result
    assert "guardrail_feedback" in result
    assert len(result["assets"]) >= 2
    assert result["chain"].chain_id == "chain-1"
    # Mock 模式下 guardrail 应通过（返回有效 JSON）
    assert result["guardrail_passed"] is True
    assert result["guardrail_feedback"] == ""


def test_run_red_chain_with_guardrail_cleans_up():
    """run_red_chain_with_guardrail 完成后应清理 output_guardrails。"""
    if not _SDK_GUARDRAIL_AVAILABLE:
        return

    orch = CyberOrchestrator(mock=_CyberMockProvider())

    # 确保开始前为空
    assert orch.exploit_planner._sdk_agent.output_guardrails == []

    orch.run_red_chain_with_guardrail("10.0.0.0/24")

    # 完成后应清理
    assert orch.exploit_planner._sdk_agent.output_guardrails == []


def test_guardrail_validates_empty_chain():
    """guardrail 校验空链时应触发 tripwire。"""
    if not _SDK_GUARDRAIL_AVAILABLE:
        return

    from agents.guardrail import GuardrailFunctionOutput, RunContextWrapper

    guardrail = CyberOrchestrator.create_attack_chain_guardrail()
    assert guardrail is not None

    # 模拟空链产出
    empty_output = {
        "chain_id": "",
        "target": "10.0.0.0/24",
        "steps": [],
        "status": "planned",
    }

    wrapper = RunContextWrapper(context=None)
    result = guardrail.guardrail_function(wrapper, None, empty_output)

    assert isinstance(result, GuardrailFunctionOutput)
    assert result.tripwire_triggered is True
    assert "chain_id" in result.output_info or "steps" in result.output_info


def test_guardrail_passes_valid_chain():
    """guardrail 校验有效链时应通过。"""
    if not _SDK_GUARDRAIL_AVAILABLE:
        return

    from agents.guardrail import GuardrailFunctionOutput, RunContextWrapper

    guardrail = CyberOrchestrator.create_attack_chain_guardrail()
    assert guardrail is not None

    valid_output = {
        "chain_id": "chain-1",
        "target": "10.0.0.0/24",
        "steps": [
            {"step_id": "s-1", "technique": "T1110", "from_asset": "a-1", "to_asset": "a-2", "success": True}
        ],
        "status": "planned",
    }

    wrapper = RunContextWrapper(context=None)
    result = guardrail.guardrail_function(wrapper, None, valid_output)

    assert isinstance(result, GuardrailFunctionOutput)
    assert result.tripwire_triggered is False
    assert "passed" in result.output_info.lower()
