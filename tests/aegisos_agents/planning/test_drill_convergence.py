# date: 2026-09-04
# dev: AegisOS
# changelog: R1 新增——多轮收敛演练内核（run_drill）/ 事件合成 / 收敛判定单测

"""R1：多轮收敛演练内核 `run_drill` 单测。

覆盖：
    - 事件合成 `_synthesize_event_stream`：首轮全量 / 后续 carry 增量 + 按 step_id 去重；
    - 收敛判定 `_evaluate_stop`：aborted / max_rounds / converged / no_progress 四规则 + 优先级；
    - `run_drill` 端到端：在 R1.5 演化 mock 下能稳定跑出多轮并在某轮收敛，
      既有 `run_red_chain(target_range)` 无参调用行为不变。
"""

from __future__ import annotations

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks.cyber_provider import _CyberMockProvider
from protocol.cyber import AttackChain, AttackStep


def _chain(*steps: AttackStep) -> AttackChain:
    return AttackChain(
        chain_id="chain-1",
        target="asset-1",
        steps=list(steps),
        status="planned",
    )


def _step(sid: str, to_asset: str = "asset-1") -> AttackStep:
    return AttackStep(
        step_id=sid,
        technique="T1110",
        from_asset="external",
        to_asset=to_asset,
        success=True,
    )


# ---------- 事件合成 ----------

def test_synthesize_event_stream_round1_full():
    """首轮：全部步骤映射为事件，carry_forward=False。"""
    events = CyberOrchestrator._synthesize_event_stream(
        _chain(_step("step-1"), _step("step-2")), [], 1
    )
    assert len(events) == 2
    assert all(not e["carry_forward"] for e in events)
    assert {e["step_id"] for e in events} == {"step-1", "step-2"}


def test_synthesize_event_stream_incremental_only_current_round():
    """R18：后续轮事件流仅含本轮链步骤，不跨轮 carry 旧事件。

    真实 LLM 每轮重新编号 S-001..N 但内容全新，旧版 carry 会把上一轮旧事件
    残留在本轮事件流里，导致蓝队告警与本轮攻击链不同源、紫队 reviewer 必然
    判 inconsistent（drill-e7ada3a1 根因）。现契约：事件流恒为本轮全量、
    carry_forward 恒为 False。
    """
    prev = CyberOrchestrator._synthesize_event_stream(
        _chain(_step("step-1")), [], 1
    )
    events = CyberOrchestrator._synthesize_event_stream(
        _chain(_step("step-1"), _step("step-2")), prev, 2
    )
    ids = {e["step_id"] for e in events}
    assert ids == {"step-1", "step-2"}
    assert all(not e["carry_forward"] for e in events)
    assert all(e["round"] == 2 for e in events)


def test_synthesize_event_stream_repeat_round_still_full():
    """R18：本轮链步骤与上轮相同也全量输出（事件流与本轮链严格同源）。"""
    prev = CyberOrchestrator._synthesize_event_stream(
        _chain(_step("step-1")), [], 1
    )
    events = CyberOrchestrator._synthesize_event_stream(_chain(_step("step-1")), prev, 2)
    # 不再 carry：本轮链 1 步→1 事件，且不标 carry_forward
    assert len(events) == 1
    assert events[0]["carry_forward"] is False
    assert events[0]["step_id"] == "step-1"


# ---------- 收敛判定 ----------

def test_evaluate_stop_aborted():
    stop, code = CyberOrchestrator._evaluate_stop(
        round=1, max_rounds=5, new_steps=[_step("s1")],
        purple_critique_valid=False, consecutive_no_new=0, aborted=True,
    )
    assert stop and code == "aborted"


def test_evaluate_stop_max_rounds():
    stop, code = CyberOrchestrator._evaluate_stop(
        round=5, max_rounds=5, new_steps=[_step("s1")],
        purple_critique_valid=False, consecutive_no_new=0,
    )
    assert stop and code == "max_rounds"


def test_evaluate_stop_converged():
    stop, code = CyberOrchestrator._evaluate_stop(
        round=2, max_rounds=5, new_steps=[], purple_critique_valid=True,
        consecutive_no_new=1,
    )
    assert stop and code == "converged"


def test_evaluate_stop_no_progress_after_two_zero():
    stop, code = CyberOrchestrator._evaluate_stop(
        round=3, max_rounds=5, new_steps=[], purple_critique_valid=False,
        consecutive_no_new=2,
    )
    assert stop and code == "no_progress"


def test_evaluate_stop_running_when_new_steps():
    stop, code = CyberOrchestrator._evaluate_stop(
        round=1, max_rounds=5, new_steps=[_step("s1")],
        purple_critique_valid=False, consecutive_no_new=0,
    )
    assert not stop and code == "running"


# ---------- run_drill 端到端（演化 mock 下多轮收敛） ----------

def _make_orchestrator():
    return CyberOrchestrator(mock=_CyberMockProvider())


def test_run_drill_multiround_converges():
    """演化 mock 下 run_drill 稳定跑出多轮并在某轮收敛（rounds>1）。"""
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5)
    assert result["rounds_executed"] > 1
    assert result["convergence_code"] == "converged"
    assert 1 < result["rounds_executed"] <= 5
    # 收敛轮：无新步骤且紫队 valid
    last = result["rounds"][-1]
    assert last["purple"]["valid"] is True
    assert last["red"]["new_steps"] == []


def test_run_drill_on_round_callback_invoked():
    """on_round 回调每轮触发一次，且携带顺序轮次号。"""
    orch = _make_orchestrator()
    seen: list[int] = []
    result = orch.run_drill(
        "10.0.0.0/24", max_rounds=5, on_round=lambda data, r: seen.append(r)
    )
    assert seen == list(range(1, len(seen) + 1))
    assert len(seen) == result["rounds_executed"]


def test_run_drill_max_rounds_cap():
    """非演化 mock（无 round 演化时红队无新步骤）→ 靠证据收敛或上限兜底。"""
    # 使用默认构造但强制 max_rounds=1 验证上限兜底不越界
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=1)
    assert result["convergence_code"] in ("converged", "max_rounds")
    assert result["rounds_executed"] == 1


def test_run_red_chain_legacy_signature_unchanged():
    """既有无参调用 run_red_chain(target_range) 行为不变（2 资产 1 步骤）。"""
    orch = _make_orchestrator()
    red = orch.run_red_chain("10.0.0.0/24")
    assert len(red["assets"]) >= 2
    assert len(red["chain"].steps) >= 1
    assert red["chain"].chain_id == "chain-1"
