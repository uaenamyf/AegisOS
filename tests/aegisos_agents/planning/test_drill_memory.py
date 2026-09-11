# date: 2026-09-05
# dev: AegisOS
# changelog: R8 新增——跨轮记忆与上下文压缩（紫队带历史决策摘要）单测

"""R8：跨轮记忆与上下文压缩（紫队带历史决策摘要）单测。

覆盖：
    - `run_drill(memory=...)`：每轮紫队评审后写记忆 → 压缩 → 下一轮注入
      `prior_rounds_summary`；总结报告含 `memory_trace`；
    - 记忆确实写入 working（decision 包）与 episodic（历史经验）；
    - 小预算触发 compactor 压缩（出现 digest 包）；
    - 不传 memory 时完全保持旧行为（无 memory_trace / 无 prior_rounds_summary）；
    - `run_purple_review` 显式传 `prior_rounds_summary` 不破坏 mock 按轮演化。
"""

from __future__ import annotations

from aegisos_agents.memory.memory_store import MemoryStore
from aegisos_agents.planning.orchestrator import CyberOrchestrator
from backend.mocks.cyber_provider import _CyberMockProvider


def _make_orchestrator() -> CyberOrchestrator:
    return CyberOrchestrator(mock=_CyberMockProvider())


def test_run_drill_memory_enabled_produces_trace():
    """传 memory 时：多轮收敛，每轮写记忆并生成下轮摘要，summary 含 memory_trace。"""
    orch = _make_orchestrator()
    memory = MemoryStore()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5, memory=memory)

    assert result["rounds_executed"] > 1  # 演化 mock 下多轮真实推进
    assert result["convergence_code"] == "converged"
    trace = result["summary"]["memory_trace"]
    assert len(trace) == result["rounds_executed"]  # 每轮一条轨迹

    # 轨迹条目字段齐全
    for entry in trace:
        assert entry["round"] >= 1
        assert entry["stored_task_id"].startswith("drill_10.0.0.0_24:r")
        assert entry["packet_summary"]
        assert entry["compressed_count"] >= 1

    # 第 2 轮起的战报携带 prior_rounds_summary（第 1 轮无前序摘要）
    rounds = result["rounds"]
    assert rounds[0]["prior_rounds_summary"] is None
    for r in rounds[1:]:
        assert r["prior_rounds_summary"], f"round {r['round']} 缺少跨轮摘要"


def test_run_drill_memory_writes_working_and_episodic():
    """决策包确实写入工作记忆（decision）与情景记忆（历史经验）。"""
    orch = _make_orchestrator()
    memory = MemoryStore()
    drill_id = "drill_10.0.0.0_24"
    orch.run_drill("10.0.0.0/24", max_rounds=5, memory=memory)

    # 工作记忆栈：drill_id 会话下决策包存在
    stack = memory.working.get(drill_id)
    assert len(stack) >= 1
    decisions = [p for p in stack if p.kind == "decision"]
    assert decisions, "工作记忆应含 decision 类包"
    assert all(p.session_id == drill_id for p in stack)

    # 情景记忆：跨会话历史经验（decision 自动路由）
    episodic = memory.episodic.all()
    assert any(p.task_id.startswith(f"{drill_id}:r") for p in episodic)


def test_run_drill_memory_small_budget_compresses():
    """小预算触发 compactor：非决策记忆被合并为 digest，保留决策包。"""
    orch = _make_orchestrator()
    memory = MemoryStore()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5, memory=memory, memory_budget=10)

    # 压缩后的工作记忆栈含 digest 包（且 digest 带溯源 task_id 列表）
    stack = memory.working.get("drill_10.0.0.0_24")
    digests = [p for p in stack if p.kind == "digest"]
    assert digests, "小预算下应出现 digest 摘要包"
    assert all(p.compression.get("count", 0) >= 1 for p in digests)
    # digest 溯源应包含被压缩的细节包（:detail task_id）
    digested_ids = [i for p in digests for i in p.compression.get("ids", [])]
    assert any(":detail" in i for i in digested_ids)
    # 决策包仍在（决策保留策略）
    assert any(p.kind == "decision" for p in stack)
    # 轨迹记录的摘要文本非空
    assert result["summary"]["memory_trace"]


def test_run_drill_without_memory_unchanged():
    """不传 memory：旧行为完全保留（无 memory_trace / 无 prior_rounds_summary）。"""
    orch = _make_orchestrator()
    result = orch.run_drill("10.0.0.0/24", max_rounds=5)
    assert "memory_trace" not in result["summary"]
    for r in result["rounds"]:
        assert "prior_rounds_summary" not in r


def test_run_purple_review_with_prior_summary_keeps_evolution():
    """run_purple_review 显式传 prior_rounds_summary：mock 按轮演化不受干扰。"""
    orch = _make_orchestrator()
    red = orch.run_red_chain("10.0.0.0/24", round=4)
    blue = orch.run_blue_chain(orch._synthesize_event_stream(red["chain"], [], 4))

    with_prior = orch.run_purple_review(
        chain=red["chain"],
        plan=blue["plan"],
        alerts=blue["alerts"],
        round=4,
        prior_rounds_summary="round 3: valid=False new_issues=1 code=no_progress",
    )
    # R18d：mock 紫队按轮演化，round4 起补齐（valid=True），prior_summary 不干预
    assert with_prior["critique"]["valid"] is True  # 末轮补齐
    assert "critique" in with_prior and "review" in with_prior


# date: 2026-09-11
# dev: AegisOS
# changelog: 新增长程攻防不漂移回归测试，锁定目标、事件同源与记忆归属不变量
def test_long_range_drill_preserves_target_and_memory_scope():
    """五轮长程演练中，目标范围、红蓝事件和记忆不得发生漂移。"""
    orch = _make_orchestrator()
    memory = MemoryStore()
    target_range = "192.168.10.0/24"
    drill_id = "drill-long-scope"

    result = orch.run_drill(
        target_range,
        max_rounds=5,
        min_rounds=5,
        drill_id=drill_id,
        memory=memory,
    )

    assert result["rounds_executed"] == 5
    assert [item["round"] for item in result["rounds"]] == [1, 2, 3, 4, 5]

    for round_data in result["rounds"]:
        round_no = round_data["round"]
        recon_trace = next(
            trace for trace in round_data["red"]["agent_trace"] if trace["agent"] == "recon"
        )
        assert target_range in recon_trace["input"]

        red_step_ids = {step["step_id"] for step in round_data["red"]["steps"]}
        event_step_ids = {event["step_id"] for event in round_data["event_stream"]}
        assert event_step_ids == red_step_ids
        assert {event["round"] for event in round_data["event_stream"]} == {round_no}

        detector_trace = next(
            trace for trace in round_data["blue"]["agent_trace"] if trace["agent"] == "detector"
        )
        assert all(
            event["step_id"] in detector_trace["input"]
            for event in round_data["event_stream"]
        )

    stack = memory.working.get(drill_id)
    assert stack
    assert all(packet.session_id == drill_id for packet in stack)
    original_packets = [packet for packet in stack if packet.kind != "digest"]
    assert original_packets
    assert all(packet.task_id.startswith(f"{drill_id}:r") for packet in original_packets)
    assert all(
        packet.task_id.startswith(drill_id) or packet.kind == "digest"
        for packet in stack
    )
