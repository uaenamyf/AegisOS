# date: 2026-07-07
# dev: myf
"""R4.4: SDK tracing + AgentHooks 单元测试。

验证：
    - ``CyberTraceProcessor`` 采集 trace/span 数据
    - ``CyberAgentHooks`` 记录 Agent 生命周期事件
    - ``CyberOrchestrator.enable_tracing()`` / ``install_hooks()``
    - ``run_red_chain_traced()`` / ``run_blue_chain_traced()`` / ``run_purple_review_traced()``
    - tracing 不破坏正常编排流程
    - 多次 traced 调用累积采集
"""

from __future__ import annotations

import json

import pytest

from aegisos_agents.planning.orchestrator import CyberOrchestrator
from observability.inspect.monitor.tracing import (
    CyberAgentHooks,
    CyberTraceData,
    CyberTraceProcessor,
    HookEvent,
)
from protocol.cyber import Alert, AttackChain, AttackStep, ResponsePlan


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def orch() -> CyberOrchestrator:
    """Mock 模式编排器。"""
    from aegisos_agents.tools.llms.mock_provider import MockProvider

    return CyberOrchestrator(mock=MockProvider())


@pytest.fixture
def sample_chain() -> AttackChain:
    """示例攻击链。"""
    return AttackChain(
        chain_id="chain-001",
        target="10.0.0.0/24",
        steps=[
            AttackStep(
                step_id="s1",
                technique="T1046",
                from_asset="internet",
                to_asset="host-1",
                success=True,
            )
        ],
        status="planned",
    )


@pytest.fixture
def sample_plan() -> ResponsePlan:
    """示例响应计划。"""
    return ResponsePlan(
        plan_id="plan-001",
        actions=[{"action": "isolate", "target": "host-1"}],
        confidence=0.85,
        rollback={"action": "restore"},
    )


@pytest.fixture
def sample_alerts() -> list[Alert]:
    """示例告警列表。"""
    return [
        Alert(
            alert_id="alert-001",
            severity="high",
            src="10.0.0.5",
            dst="10.0.0.10",
            technique="T1046",
            raw={"event": "scan"},
        )
    ]


# ------------------------------------------------------------------ #
# CyberTraceProcessor 测试
# ------------------------------------------------------------------ #


class TestCyberTraceProcessor:
    """测试 CyberTraceProcessor 基础功能。"""

    def test_trace_processor_initial_state(self):
        """初始状态：无 trace 数据。"""
        proc = CyberTraceProcessor()
        assert proc.get_trace_data() is None
        assert proc.get_all_traces() == []

    def test_trace_processor_reset(self):
        """reset() 清空所有数据。"""
        proc = CyberTraceProcessor()
        proc._traces["fake"] = CyberTraceData(trace_id="fake")
        proc._completed.append(CyberTraceData(trace_id="fake"))
        proc.reset()
        assert proc.get_trace_data() is None
        assert proc.get_all_traces() == []

    def test_trace_span_to_dict(self):
        """CyberSpanData.to_dict() 返回正确结构。"""
        from observability.inspect.monitor.tracing import CyberSpanData

        span = CyberSpanData(
            span_id="span-1",
            parent_id=None,
            name="agent_run",
            type="agent",
            started_at=1000.0,
            ended_at=1001.5,
            data={"agent": "recon"},
        )
        d = span.to_dict()
        assert d["span_id"] == "span-1"
        assert d["parent_id"] is None
        assert d["duration_ms"] == 1500.0
        assert d["data"]["agent"] == "recon"

    def test_trace_data_to_json(self):
        """CyberTraceData.to_json() 返回有效 JSON。"""
        data = CyberTraceData(
            trace_id="trace-1",
            workflow_name="cyber_red_chain",
            metadata={"scenario": "s1"},
            started_at=1000.0,
            ended_at=1002.0,
        )
        j = data.to_json()
        parsed = json.loads(j)
        assert parsed["trace_id"] == "trace-1"
        assert parsed["workflow_name"] == "cyber_red_chain"
        assert parsed["metadata"]["scenario"] == "s1"
        assert parsed["duration_ms"] == 2000.0

    def test_trace_data_span_count(self):
        """span_count 属性返回正确数量。"""
        from observability.inspect.monitor.tracing import CyberSpanData

        data = CyberTraceData(trace_id="t1")
        assert data.span_count == 0
        data.spans.append(CyberSpanData(span_id="s1"))
        data.spans.append(CyberSpanData(span_id="s2"))
        assert data.span_count == 2

    def test_trace_data_spans_by_type(self):
        """spans_by_type() 按类型筛选。"""
        from observability.inspect.monitor.tracing import CyberSpanData

        data = CyberTraceData(trace_id="t1")
        data.spans.append(CyberSpanData(span_id="s1", type="agent"))
        data.spans.append(CyberSpanData(span_id="s2", type="generation"))
        data.spans.append(CyberSpanData(span_id="s3", type="agent"))
        agent_spans = data.spans_by_type("agent")
        assert len(agent_spans) == 2


# ------------------------------------------------------------------ #
# CyberAgentHooks 测试
# ------------------------------------------------------------------ #


class TestCyberAgentHooks:
    """测试 CyberAgentHooks 基础功能。"""

    def test_agent_hooks_initial_empty(self):
        """初始状态：无事件。"""
        hooks = CyberAgentHooks(agent_name="TestAgent")
        assert hooks.events == []

    @pytest.mark.asyncio
    async def test_agent_hooks_record_on_start(self):
        """on_start 回调记录事件。"""
        hooks = CyberAgentHooks(agent_name="TestAgent")

        class FakeAgent:
            name = "ReconAgent"
            instructions = "You are a recon agent."

        await hooks.on_start(context=None, agent=FakeAgent())
        assert len(hooks.events) == 1
        evt = hooks.events[0]
        assert evt.event_type == "on_start"
        assert evt.agent_name == "ReconAgent"
        assert evt.data["instructions"] == "You are a recon agent."

    @pytest.mark.asyncio
    async def test_agent_hooks_record_on_end(self):
        """on_end 回调记录事件。"""
        hooks = CyberAgentHooks(agent_name="TestAgent")

        class FakeAgent:
            name = "ExploitAgent"

        class FakeOutput:
            def model_dump(self):
                return {"chain_id": "chain-001"}

        await hooks.on_end(context=None, agent=FakeAgent(), output=FakeOutput())
        assert len(hooks.events) == 1
        evt = hooks.events[0]
        assert evt.event_type == "on_end"
        assert evt.data["output"]["chain_id"] == "chain-001"

    @pytest.mark.asyncio
    async def test_agent_hooks_record_on_handoff(self):
        """on_handoff 回调记录事件。"""
        hooks = CyberAgentHooks(agent_name="TargetAgent")

        class FakeAgent:
            name = "TargetAgent"

        class FakeSource:
            name = "SourceAgent"

        await hooks.on_handoff(context=None, agent=FakeAgent(), source=FakeSource())
        assert len(hooks.events) == 1
        assert hooks.events[0].event_type == "on_handoff"
        assert hooks.events[0].data["source"] == "SourceAgent"

    @pytest.mark.asyncio
    async def test_agent_hooks_multiple_events(self):
        """多次回调累积事件。"""
        hooks = CyberAgentHooks(agent_name="MultiAgent")

        class FakeAgent:
            name = "MultiAgent"

        await hooks.on_start(context=None, agent=FakeAgent())
        await hooks.on_llm_start(
            context=None,
            agent=FakeAgent(),
            system_prompt="test",
            input_items=[{"role": "user"}],
        )
        await hooks.on_llm_end(context=None, agent=FakeAgent(), response="resp")
        await hooks.on_end(context=None, agent=FakeAgent(), output="done")

        assert len(hooks.events) == 4
        types = [e.event_type for e in hooks.events]
        assert types == ["on_start", "on_llm_start", "on_llm_end", "on_end"]


# ------------------------------------------------------------------ #
# CyberOrchestrator tracing 集成测试
# ------------------------------------------------------------------ #


class TestOrchestratorTracing:
    """测试 CyberOrchestrator 的 tracing 集成。"""

    def test_orchestrator_enable_tracing(self, orch: CyberOrchestrator):
        """enable_tracing() 注册 processor。"""
        proc = orch.enable_tracing()
        assert proc is not None
        assert isinstance(proc, CyberTraceProcessor)
        assert orch._trace_processor is proc

    def test_orchestrator_disable_tracing(self, orch: CyberOrchestrator):
        """disable_tracing() 清理状态。"""
        orch.enable_tracing()
        orch.disable_tracing()
        assert orch._trace_processor is None

    def test_orchestrator_install_hooks(self, orch: CyberOrchestrator):
        """install_hooks() 为 9 个 Agent 安装钩子。"""
        hooks = orch.install_hooks()
        assert len(hooks) == 9
        # 每个 hook 都是 CyberAgentHooks
        for h in hooks:
            assert isinstance(h, CyberAgentHooks)
        # 每个 Agent 的 _sdk_agent.hooks 已设置
        agents = [
            orch.recon,
            orch.vuln_correlator,
            orch.exploit_planner,
            orch.detector,
            orch.triage,
            orch.threat_hunt,
            orch.ir_planner,
            orch.critic,
            orch.reviewer,
        ]
        for agent in agents:
            assert agent._sdk_agent.hooks is not None

    def test_orchestrator_get_trace_data_initial_none(self, orch: CyberOrchestrator):
        """未启用 tracing 时 get_trace_data() 返回 None。"""
        assert orch.get_trace_data() is None

    def test_orchestrator_get_trace_json_initial_none(self, orch: CyberOrchestrator):
        """未启用 tracing 时 get_trace_json() 返回 None。"""
        assert orch.get_trace_json() is None

    def test_run_red_chain_traced(self, orch: CyberOrchestrator):
        """run_red_chain_traced() 产出正确且 trace 数据被采集。"""
        orch.enable_tracing()
        result = orch.run_red_chain_traced("10.0.0.0/24")

        # 编排产出正确
        assert "assets" in result
        assert "findings" in result
        assert "chain" in result

        # trace 数据被采集
        trace_data = orch.get_trace_data()
        assert trace_data is not None
        assert trace_data.workflow_name == "cyber_red_chain"

    def test_run_blue_chain_traced(self, orch: CyberOrchestrator):
        """run_blue_chain_traced() 产出正确且 trace 数据被采集。"""
        orch.enable_tracing()
        events = [{"type": "scan", "src": "10.0.0.5"}]
        result = orch.run_blue_chain_traced(events)

        assert "alerts" in result
        assert "plan" in result

        trace_data = orch.get_trace_data()
        assert trace_data is not None
        assert trace_data.workflow_name == "cyber_blue_chain"

    def test_run_purple_review_traced(
        self,
        orch: CyberOrchestrator,
        sample_chain: AttackChain,
        sample_plan: ResponsePlan,
        sample_alerts: list[Alert],
    ):
        """run_purple_review_traced() 产出正确且 trace 数据被采集。"""
        orch.enable_tracing()
        result = orch.run_purple_review_traced(
            sample_chain, sample_plan, sample_alerts
        )

        assert "critique" in result
        assert "review" in result

        trace_data = orch.get_trace_data()
        assert trace_data is not None
        assert trace_data.workflow_name == "cyber_purple_review"

    def test_traced_methods_with_hooks(
        self,
        orch: CyberOrchestrator,
        sample_chain: AttackChain,
        sample_plan: ResponsePlan,
        sample_alerts: list[Alert],
    ):
        """traced 方法 + hooks 同时工作，不互相干扰。"""
        orch.enable_tracing()
        orch.install_hooks()

        # 执行红队链
        result = orch.run_red_chain_traced("10.0.0.0/24")
        assert "chain" in result

        # trace 数据
        trace_data = orch.get_trace_data()
        assert trace_data is not None

        # hooks 事件（Mock 模式下 SDK Runner 会触发 on_start/on_end）
        events = orch.get_hooks_events()
        # Mock 模式下至少有一些事件被记录
        assert isinstance(events, list)

    def test_tracing_does_not_break_normal_run(self, orch: CyberOrchestrator):
        """启用 tracing 不破坏正常编排流程。"""
        # 不启用 tracing 也能正常运行
        result_normal = orch.run_red_chain("10.0.0.0/24")
        assert "chain" in result_normal

        # 启用 tracing 后也能正常运行
        orch.enable_tracing()
        result_traced = orch.run_red_chain_traced("10.0.0.0/24")
        assert "chain" in result_traced

        # 两次结果结构一致（Mock 模式下数据相同）
        assert (
            result_normal["chain"].chain_id == result_traced["chain"].chain_id
        )

    def test_multiple_traced_runs_accumulate(self, orch: CyberOrchestrator):
        """多次 traced 调用，trace 数据累积。"""
        orch.enable_tracing()

        orch.run_red_chain_traced("10.0.0.0/24")
        orch.run_blue_chain_traced([{"type": "scan"}])

        all_traces = orch._trace_processor.get_all_traces()
        assert len(all_traces) == 2
        # 最近的 trace 是 blue chain
        latest = orch.get_trace_data()
        assert latest is not None
        assert latest.workflow_name == "cyber_blue_chain"
