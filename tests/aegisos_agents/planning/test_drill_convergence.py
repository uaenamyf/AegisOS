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


# ---------- R19：非收敛停止码的结论话术（不暗示失败） ----------

def test_run_drill_max_rounds_conclusion_wording():
    """跑满轮次上限时，结论应为「充分探索 N 轮、遗留 M 个待验证缺口」。

    真实 LLM 模式下打满 max_rounds 是常态而非失败——措辞不得暗示"未收敛/
    未通过"，避免演示时被误读为系统故障（用户 2026-09-13 需求）。
    """
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=1)
    assert result["convergence_code"] == "max_rounds"
    conclusion = result["summary"]["conclusion"]
    assert "充分探索 1 轮" in conclusion
    assert "待验证缺口" in conclusion
    assert "convergence_code" not in conclusion
    # 不暗示失败
    assert "未通过" not in conclusion
    assert "未收敛" not in conclusion


def test_run_drill_converged_conclusion_wording():
    """真收敛时结论保留「达成收敛」原话术。"""
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5)
    assert result["convergence_code"] == "converged"
    assert "达成收敛" in result["summary"]["conclusion"]


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


# ---------- R19：收敛可达性（真实模式 5 轮永不收敛的根因回归） ----------


def _step_t(sid: str, to_asset: str, technique: str) -> AttackStep:
    return AttackStep(
        step_id=sid,
        technique=technique,
        from_asset="external",
        to_asset=to_asset,
        success=True,
    )


def test_fingerprint_ignores_prose_and_cve_churn():
    """同一技法边：散文改写 / 换 CVE 不得算新增（旧版指纹含 technique 全文）。

    真实 LLM 对同一条边每轮换措辞、换 CVE，旧指纹把它当成全新步骤，
    导致 new_steps 恒非空、converged/no_progress 数学上不可达。
    """
    a = _step_t("S-001", "asset-001", "T1210 (CVE-2024-6387 on asset-001)")
    b = _step_t("S-001", "asset-001", "T1210")
    c = _step_t("S-009", "asset-001", "exploited CVE-2021-3150 via T1210 lateral movement")
    fp = CyberOrchestrator._step_fingerprint
    assert fp(a) == fp(b) == fp(c)


def test_fingerprint_still_distinguishes_real_progress():
    """技法编号或端点不同必须仍判为不同（不能退化成恒等）。"""
    fp = CyberOrchestrator._step_fingerprint
    t1210 = _step_t("S-1", "asset-001", "T1210")
    assert fp(t1210) != fp(_step_t("S-1", "asset-002", "T1210")), "端点不同应视为新攻击面"
    assert fp(t1210) != fp(_step_t("S-1", "asset-001", "T1190")), "技法不同应视为新攻击面"
    assert fp(t1210) != fp(_step_t("S-1", "asset-001", "T1021.002")), "子技术不同应区分"


def test_cumulative_diff_terminates_variant_flapping():
    """模型在两个链变体间来回切换时，累计集能判"无新增"，逐轮比对不能。

    这正是 drill-7b797871 永不收敛的机制：r4 换 B 链、r5 又切回 A 链变体，
    只比上一轮时每轮都"全新增"。
    """
    chain_a = _chain(_step_t("S-1", "asset-001", "T1210 (CVE-2024-6387)"))
    chain_b = _chain(_step_t("S-1", "asset-002", "T1190 (CVE-2023-28425)"))

    explored: set = set()
    per_round_new: list[int] = []
    cum_new: list[int] = []
    prev: AttackChain | None = None
    for chain in (chain_a, chain_b, chain_a, chain_b):  # 来回横跳
        per_round_new.append(
            len(CyberOrchestrator._diff_chain_steps(prev, chain))
        )
        cum_new.append(
            len(CyberOrchestrator._diff_chain_steps(prev, chain, explored))
        )
        explored |= {
            CyberOrchestrator._step_fingerprint(s) for s in chain.steps
        }
        prev = chain

    # 逐轮比对：每次都把对方当新增 → 永不归零（旧 bug）
    assert per_round_new == [1, 1, 1, 1]
    # 累计集：第 3 轮起无新增 → no_progress 可达
    assert cum_new == [1, 1, 0, 0]


def test_evaluate_stop_no_progress_reachable_end_to_end():
    """累计指纹喂给 _evaluate_stop 时应能产出 no_progress（而非只能 max_rounds）。"""
    stop, code = CyberOrchestrator._evaluate_stop(
        round=3,
        max_rounds=5,
        new_steps=[],
        purple_critique_valid=False,
        consecutive_no_new=2,
    )
    assert stop and code == "no_progress"
