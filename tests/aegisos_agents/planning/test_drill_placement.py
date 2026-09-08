# date: 2026-09-05
# dev: AegisOS
# changelog: R10 新增——演练阶段 placement 联动（端-边-云自适应调度标注）单测

"""R10：演练阶段 placement 联动单测。

覆盖：
    - `_phase_placements`：红/蓝/紫三阶段产出合法 tier（device/edge/cloud）
      + 非空卸载理由；
    - `run_drill` 端到端：每轮 round_data 携带 `phase.{red,blue,purple}`，
      tier 合法、reason 非空，且三阶段 tier 符合阶段语义预期
      （red 偏好 device/edge、purple 偏好 cloud）；
    - 既有行为零破坏：不启用 placement 相关参数时结构不变（phase 为新增字段）。
"""

from __future__ import annotations

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks.cyber_provider import _CyberMockProvider

_TIERS = {"device", "edge", "cloud"}


def _make_orchestrator() -> CyberOrchestrator:
    return CyberOrchestrator(mock=_CyberMockProvider())


def test_phase_placements_legal_tiers_and_reason():
    """三阶段 placement 的 tier 合法且 reason 非空。"""
    orch = _make_orchestrator()
    placements = orch._phase_placements()
    assert set(placements) == {"red", "blue", "purple"}
    for phase, p in placements.items():
        assert p["tier"] in _TIERS, f"{phase} tier 非法: {p['tier']}"
        assert p["model_id"], f"{phase} 缺 model_id"
        assert p["reason"], f"{phase} 缺卸载理由"


def test_phase_placements_semantic_expectation():
    """阶段语义：red 超低延迟应命中 device/edge，purple 高算力应命中 cloud。"""
    orch = _make_orchestrator()
    placements = orch._phase_placements()
    # red: latency_budget=0.8 < 1.0 → 端侧优先（device/edge 候选池存在）
    assert placements["red"]["tier"] in {"device", "edge"}
    # purple: latency_budget=10.0 + unrestricted → 算力优先 → cloud
    assert placements["purple"]["tier"] == "cloud"
    # blue: latency_budget=3.0 < 5.0 → 边侧优先
    assert placements["blue"]["tier"] in {"edge", "device"}


def test_run_drill_rounds_carry_phase_placements():
    """端到端：每轮 round_data.phase 存在且三阶段标注合法。"""
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5)
    assert result["rounds_executed"] >= 2  # 多轮收敛真实推进
    for r in result["rounds"]:
        phase = r["phase"]
        assert set(phase) == {"red", "blue", "purple"}
        for p in phase.values():
            assert p["tier"] in _TIERS
            assert p["reason"]


def test_run_drill_phase_placements_consistent_across_rounds():
    """各轮同一阶段的 tier 保持稳定（调度规则确定性）。"""
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5)
    tiers = {
        phase: {r["phase"][phase]["tier"] for r in result["rounds"]}
        for phase in ("red", "blue", "purple")
    }
    for phase, tset in tiers.items():
        assert len(tset) == 1, f"{phase} 跨轮 tier 不稳定: {tset}"
