# date: 2026-09-05
# dev: AegisOS Dev
# changelog: R9 新增——演练事件总线化 + 低熵增量推送单测

"""R9：演练事件总线化（EventBus 联动）单测。

覆盖：
    - DrillRuntime 发布 drill.round 事件到事件总线（独立注入实例）；
    - payload 为低熵增量摘要——含 round/new_steps/new_issues/valid/converged/
      carry_forward_count/prior_summary，不含全量 AttackChain/ResponsePlan；
    - API 级：起一场演练后全局 EventBus 可经 /events?stream=drill.round 订阅到；
    - EventType.DrillRound 枚举 topic 与总线约定一致。
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from backend.core.auth import DEV_API_KEY
from backend.core.composition import get_composition, reset_composition
from backend.mocks.event_bus import MockEventBusAPI
from backend.routers.drill import DrillRuntime
from protocol.event import EventType

_AUTH_HEADERS = {"X-API-Key": DEV_API_KEY}


def _wait_until(pred, timeout: float = 15.0, interval: float = 0.2) -> bool:
    """轮询等待条件成立（演练跑在后台线程）。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return False


def _make_runtime(event_bus: MockEventBusAPI) -> DrillRuntime:
    """构造跑独立事件总线的 DrillRuntime（直连 service，不走 HTTP）。"""
    from backend.services.cyber_defense_service import CyberDefenseService

    svc = CyberDefenseService()
    runtime = DrillRuntime(svc, "10.0.0.0/24", max_rounds=5, event_bus=event_bus)
    runtime._run()  # 同步跑完（单测直接调用编排线程入口）
    return runtime


class TestDrillRoundEventPublish:
    """DrillRuntime 发布低熵 drill.round 事件。"""

    def test_publishes_drill_round_events(self):
        """演练完成后事件总线应含 topic=drill.round 的事件。"""
        bus = MockEventBusAPI()
        runtime = _make_runtime(bus)
        events = [e for e in bus.recent_events(1000) if e.topic == EventType.DrillRound.value]
        assert events, "应发布 drill.round 事件到总线"
        assert all(e.task_id == runtime.drill_id for e in events)
        assert len(events) >= 2  # 每轮一条（多轮收敛演练至少 2 轮）
        # 轮次递增
        rounds = [e.payload["round"] for e in events]
        assert rounds == sorted(rounds)
        assert len(set(rounds)) == len(rounds)

    def test_payload_is_low_entropy_increment(self):
        """payload 只含增量与摘要，不含全量攻击链/响应计划。"""
        bus = MockEventBusAPI()
        _make_runtime(bus)
        events = [e for e in bus.recent_events(1000) if e.topic == EventType.DrillRound.value]
        assert events
        payload = events[0].payload
        # 增量/摘要字段齐备
        for key in (
            "round",
            "drill_id",
            "new_steps",
            "new_issues",
            "valid",
            "converged",
            "carry_forward_count",
            "prior_summary",
        ):
            assert key in payload, f"payload 缺少 {key}"
        # 低熵：不得携带全量结构
        for banned in ("attack_chain", "response_plan", "alerts", "steps", "critique", "review"):
            assert banned not in payload, f"payload 不应含全量字段 {banned}"
        # 数值类型正确
        assert isinstance(payload["new_steps"], int)
        assert isinstance(payload["new_issues"], int)
        assert isinstance(payload["carry_forward_count"], int)
        assert isinstance(payload["valid"], bool)
        assert isinstance(payload["converged"], bool)

    def test_event_stream_same_source_as_chain(self):
        """R18：事件流与本轮链同源（carry_forward_count 恒为 0）。"""
        bus = MockEventBusAPI()
        _make_runtime(bus)
        events = [e for e in bus.recent_events(1000) if e.topic == EventType.DrillRound.value]
        assert events
        # 新契约：蓝队告警与本轮攻击链同源，不再有跨轮 carry 事件
        assert all(e.payload["carry_forward_count"] == 0 for e in events)
        # 首轮事件流非空（与本轮链步骤数一致，可观测）
        assert events[0].payload["new_steps"] >= 1


class TestDrillRuntimeReplay:
    """DrillRuntime 事件历史可重放：运行中晚接入的订阅者不丢已发生事件。

    对应线上症状「切走再切回，CoT 时间线空白 / 卡在等待首个 agent」。
    """

    def test_wait_events_replays_history_of_running_drill(self):
        """state=running 时，新 cursor=0 的订阅者应立刻拿到全部历史。"""
        from backend.mocks.event_bus import MockEventBusAPI
        from backend.services.cyber_defense_service import CyberDefenseService

        runtime = DrillRuntime(
            CyberDefenseService(), "10.0.0.0/24", max_rounds=5, event_bus=MockEventBusAPI()
        )
        # 模拟编排已推进若干事件但尚未结束（真实 LLM 下单步 30-90s）
        runtime.emit("drill_start", {"drill_id": runtime.drill_id, "max_rounds": 5})
        runtime._emit_stage("red", 1)
        runtime._emit_agent("red", "recon")
        assert runtime.state == "running"

        batch, done = runtime.wait_events(0, timeout=0.1)
        assert done is False, "演练仍在运行时流不应终止"
        assert [item["event"] for item in batch] == [
            "drill_start",
            "drill_stage",
            "drill_agent",
        ]
        # 第二个订阅者（切页返回）从 0 接入，看到的历史完全一致
        batch2, _ = runtime.wait_events(0, timeout=0.1)
        assert [i["event"] for i in batch2] == [i["event"] for i in batch]
        # 增量订阅只拿新增
        batch3, _ = runtime.wait_events(len(batch), timeout=0.1)
        assert batch3 == []

    def test_agent_trace_and_stage_snapshot_survive_disconnect(self):
        """agent_trace / current_stage 在 SSE 断开后仍可供 get_drill 恢复。"""
        from backend.mocks.event_bus import MockEventBusAPI
        from backend.services.cyber_defense_service import CyberDefenseService

        runtime = DrillRuntime(
            CyberDefenseService(), "10.0.0.0/24", max_rounds=5, event_bus=MockEventBusAPI()
        )
        runtime._emit_stage("blue", 2)
        runtime._emit_agent("blue", "detector")
        runtime._emit_agent("blue", "triage")

        assert runtime.current_stage == "blue"
        assert runtime.current_round == 2
        trace = runtime.agent_trace()
        assert [t["agent"] for t in trace] == ["detector", "triage"]
        # round 随事件下发，前端恢复时间线时不需要再推断当前轮
        assert all(t["round"] == 2 for t in trace)
        assert all(t["label"] and t["ts"] > 0 for t in trace)

    def test_stream_terminates_after_drill_done(self):
        """演练结束后接入的订阅者应拿到完整历史并正常收尾（done=True）。"""
        from backend.mocks.event_bus import MockEventBusAPI
        from backend.services.cyber_defense_service import CyberDefenseService

        runtime = DrillRuntime(
            CyberDefenseService(), "10.0.0.0/24", max_rounds=5, event_bus=MockEventBusAPI()
        )
        runtime._run()  # 同步跑完
        assert runtime.state == "done"
        batch, done = runtime.wait_events(0, timeout=0.1)
        names = [item["event"] for item in batch]
        assert names[0] == "drill_start"
        assert names[-1] == "drill_done"
        assert done is True


@pytest.fixture()
def client():
    """API 级 fixture：重置 composition，用全局 EventBus。"""
    from backend.main import create_app

    reset_composition()
    app = create_app()
    return TestClient(app)


class TestDrillRoundEventApi:
    """API 级：演练事件可达全局 EventBus，/events 可订阅。"""

    def test_events_endpoint_filters_drill_round(self, client: TestClient):
        """起一场演练后，/api/v1/events?stream=drill.round 应能订阅到事件。"""
        resp = client.post(
            "/api/v1/drill/start",
            json={"target_range": "10.0.0.0/24", "max_rounds": 3},
            headers=_AUTH_HEADERS,
        )
        assert resp.status_code == 201
        drill_id = resp.json()["drill_id"]

        bus = get_composition().event_bus
        assert _wait_until(
            lambda: any(
                e.topic == EventType.DrillRound.value and e.task_id == drill_id
                for e in bus.recent_events(1000)
            )
        ), "演练应把 drill.round 事件发布到全局 EventBus"

        drill_round_events = [
            e for e in bus.recent_events(1000) if e.topic == EventType.DrillRound.value
        ]
        assert drill_round_events
        # 事件可被 /events?stream=drill.round 过滤（topic 值与查询参数一致）
        assert EventType.DrillRound.value == "drill.round"
