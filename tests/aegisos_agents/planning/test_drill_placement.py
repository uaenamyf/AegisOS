# date: 2026-09-05
# dev: AegisOS
# changelog: R10 更新——placement 自适应调度单测（轮次负载缩放 + 可执行层约束）

"""R10：演练阶段 placement 联动单测（自适应调度）。

覆盖：
    - `_phase_placements`：红/蓝/紫三阶段产出合法 tier（device/edge/cloud）
      + 非空卸载理由；
    - 轮次自适应：随收敛负载下降，部分阶段自动卸载到更近的层
      （紫队评审云→边、蓝队防御边→端），不再是固定映射；
    - 可执行层约束：真实 LLM 模式仅云 API 可执行时，端/边偏好降级云侧执行；
    - `run_drill` 端到端：每轮 round_data 携带 `phase.{red,blue,purple}`，
      tier 合法、reason 非空。
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
    """阶段语义（第 1 轮满负载）：red 超低延迟→device，purple 高算力→cloud。"""
    orch = _make_orchestrator()
    placements = orch._phase_placements(round_no=1)
    # red: latency_budget=0.8 < 1.0 → 端侧优先（device/edge 候选池存在）
    assert placements["red"]["tier"] in {"device", "edge"}
    # purple: latency_budget=10.0 + unrestricted → 算力优先 → cloud
    assert placements["purple"]["tier"] == "cloud"
    # blue: latency_budget=3.0 < 5.0 → 边侧优先
    assert placements["blue"]["tier"] in {"edge", "device"}


def test_phase_placements_adaptive_across_rounds():
    """自适应：收敛负载下降后，紫队评审从云卸载到边侧（不再是固定映射）。"""
    orch = _make_orchestrator()
    r1 = orch._phase_placements(round_no=1)
    r4 = orch._phase_placements(round_no=4)
    # 第 1 轮：满负载 → 紫队评审上云
    assert r1["purple"]["tier"] == "cloud"
    # 第 4 轮：负载约 46% → 紫队评审降级到边侧执行（算力需求下降）
    assert r4["purple"]["tier"] == "edge"
    # 红队始终超低延迟 → 端侧不变
    assert r1["red"]["tier"] == r4["red"]["tier"] == "device"
    # 理由中标注轮次负载信息
    assert "第 4 轮" in r4["purple"]["reason"]


def test_phase_placements_real_mode_degrades_to_cloud(monkeypatch):
    """真实 LLM 模式仅云 API 可执行：端/边偏好降级云侧并在理由中说明。"""
    monkeypatch.setenv("AEGIS_USE_MOCK", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890")
    orch = _make_orchestrator()
    placements = orch._phase_placements(round_no=1)
    # 全部阶段最终都落云侧执行（当前端/边未接独立 API）
    for phase in ("red", "blue", "purple"):
        assert placements[phase]["tier"] == "cloud", f"{phase} 应降级云侧: {placements[phase]}"
    # 红/蓝偏好端/边 → 理由中显式说明降级云侧执行
    assert "降级云侧执行" in placements["red"]["reason"]
    assert "降级云侧执行" in placements["blue"]["reason"]
    # 紫队本身偏好云（高算力）→ 无需降级说明
    assert "降级云侧执行" not in placements["purple"]["reason"]


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


def test_run_drill_adaptive_tiers_change_with_rounds():
    """端到端：跨轮 placement 自适应变化（紫队云→边、蓝队边→端）。"""
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5)
    tiers = {
        phase: {r["phase"][phase]["tier"] for r in result["rounds"]}
        for phase in ("red", "blue", "purple")
    }
    # 红队始终端侧（超低延迟语义不变）
    assert tiers["red"] == {"device"}
    # 紫队评审随负载收敛从云卸载到边
    assert tiers["purple"] == {"cloud", "edge"}
    # 蓝队防御低延迟，收敛后期卸载到端
    assert tiers["blue"] == {"edge", "device"}
