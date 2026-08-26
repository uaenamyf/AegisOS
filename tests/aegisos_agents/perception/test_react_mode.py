# date: 2026-08-12
# dev: overwhelmingly
"""AP2.1 ReAct 推理循环单元测试。

覆盖 think→act→observe 正常路径、即时结束、工具失败恢复、失败快速终止、
最大轮数保护、执行接口适配与输入校验。
"""

from __future__ import annotations

import pytest

from aegisos_agents.perception.reasoning.strategies.react_mode import (
    ReactDecision,
    ReactDecisionKind,
    ReactMode,
    ReactStatus,
)
from protocol.tool import ToolCall, ToolResult


class _ExecutionPort:
    """记录调用的 ExecutionAPI 兼容测试替身。"""

    def __init__(self) -> None:
        """初始化空调用记录。"""
        self.calls: list[ToolCall] = []

    def execute(self, call: ToolCall) -> ToolResult:
        """返回与调用关联的成功观察。"""
        self.calls.append(call)
        return ToolResult(output={"host": call.args["host"]})


def test_react_decision_factories_build_valid_decisions() -> None:
    """act/finish 工厂应生成类型明确的 ReAct 决策。"""
    call = ToolCall(name="scan", args={"host": "10.0.0.1"})

    action = ReactDecision.act("需要先扫描目标", call)
    finish = ReactDecision.finish("信息已经足够", {"status": "done"})

    assert action.kind is ReactDecisionKind.Act
    assert action.action is call
    assert finish.kind is ReactDecisionKind.Finish
    assert finish.final_output == {"status": "done"}
    with pytest.raises(ValueError, match="requires"):
        ReactDecision(kind=ReactDecisionKind.Act, thought="缺少工具")
    with pytest.raises(ValueError, match="cannot include"):
        ReactDecision(
            kind=ReactDecisionKind.Finish,
            thought="不应再调用工具",
            action=call,
        )


def test_react_mode_runs_think_act_observe_until_finish() -> None:
    """循环应把工具观察传回下一轮思考并产出完整轨迹。"""
    seen_trace_lengths: list[int] = []

    def thinker(goal, trace):
        seen_trace_lengths.append(len(trace))
        assert goal == "调查目标"
        if not trace:
            return ReactDecision.act(
                "先扫描暴露服务",
                ToolCall(name="scan", args={"host": "10.0.0.1"}),
            )
        assert trace[-1].observation.output == {"ports": [22, 80]}
        return ReactDecision.finish("扫描结果足够回答", {"ports": [22, 80]})

    def executor(call):
        return ToolResult(call_id=call.call_id, output={"ports": [22, 80]})

    result = ReactMode[dict]().run_react("调查目标", thinker, executor)

    assert result.status is ReactStatus.Succeeded
    assert result.succeeded is True
    assert result.final_output == {"ports": [22, 80]}
    assert seen_trace_lengths == [0, 1]
    assert len(result.steps) == 1
    assert result.steps[0].thought == "先扫描暴露服务"
    assert result.steps[0].action.name == "scan"
    assert result.steps[0].observation.ok is True


def test_react_mode_can_finish_without_tool_call() -> None:
    """思考器已有答案时应直接结束且不调用工具。"""
    called = False

    def executor(call):
        nonlocal called
        called = True
        return ToolResult(call_id=call.call_id)

    result = ReactMode[str]().run_react(
        "回答已知问题",
        lambda goal, trace: ReactDecision.finish("无需工具", "answer"),
        executor,
    )

    assert result.status is ReactStatus.Succeeded
    assert result.final_output == "answer"
    assert result.steps == []
    assert called is False


def test_react_mode_supports_execution_api_object() -> None:
    """工具执行器应支持具有 execute 方法的 ExecutionAPI 对象。"""
    port = _ExecutionPort()

    def thinker(goal, trace):
        if not trace:
            return ReactDecision.act(
                "查询主机",
                ToolCall(name="lookup", args={"host": "asset-1"}),
            )
        return ReactDecision.finish("查询完成", trace[-1].observation.output)

    result = ReactMode[dict]().run_react("查询资产", thinker, port)

    assert result.status is ReactStatus.Succeeded
    assert result.final_output == {"host": "asset-1"}
    assert len(port.calls) == 1
    assert result.steps[0].observation.call_id == port.calls[0].call_id


def test_react_mode_turns_tool_exception_into_observation_and_recovers() -> None:
    """工具异常应成为失败观察，使思考器可以选择备选工具恢复。"""
    calls: list[str] = []

    def thinker(goal, trace):
        if not trace:
            return ReactDecision.act("尝试主动扫描", ToolCall(name="active_scan"))
        if len(trace) == 1:
            assert trace[-1].observation.ok is False
            assert "sandbox unavailable" in trace[-1].observation.error
            return ReactDecision.act("改用被动查询", ToolCall(name="passive_lookup"))
        return ReactDecision.finish("备选工具成功", trace[-1].observation.output)

    def executor(call):
        calls.append(call.name)
        if call.name == "active_scan":
            raise RuntimeError("sandbox unavailable")
        return ToolResult(call_id=call.call_id, output="recovered")

    result = ReactMode[str]().run_react("收集资产", thinker, executor)

    assert result.status is ReactStatus.Succeeded
    assert result.final_output == "recovered"
    assert calls == ["active_scan", "passive_lookup"]
    assert result.steps[0].observation.meta["exception_type"] == "RuntimeError"


def test_react_mode_can_stop_on_tool_error() -> None:
    """stop_on_tool_error 启用时应在首个失败观察后终止。"""
    result = ReactMode[None]().run_react(
        "执行工具",
        lambda goal, trace: ReactDecision.act("调用失败工具", ToolCall(name="broken")),
        lambda call: ToolResult(call_id=call.call_id, ok=False, error="denied"),
        stop_on_tool_error=True,
    )

    assert result.status is ReactStatus.Failed
    assert result.error == "denied"
    assert len(result.steps) == 1


def test_react_mode_stops_at_max_iterations() -> None:
    """思考器持续调用工具时应由最大轮数保护终止。"""
    result = ReactMode[None]().run_react(
        "持续执行",
        lambda goal, trace: ReactDecision.act(
            "继续尝试",
            ToolCall(name="noop", args={"iteration": len(trace) + 1}),
        ),
        lambda call: ToolResult(call_id=call.call_id, output="ok"),
        max_iterations=3,
    )

    assert result.status is ReactStatus.MaxIterations
    assert len(result.steps) == 3
    assert "3" in result.error


def test_react_mode_returns_failed_result_when_thinker_raises() -> None:
    """思考阶段异常应返回失败结果并保留可诊断错误。"""

    def thinker(goal, trace):
        raise ValueError("invalid model output")

    result = ReactMode[None]().run_react(
        "分析任务",
        thinker,
        lambda call: ToolResult(call_id=call.call_id),
    )

    assert result.status is ReactStatus.Failed
    assert result.steps == []
    assert "invalid model output" in result.error


def test_react_mode_rejects_invalid_arguments() -> None:
    """空目标和非正最大轮数应在执行前被拒绝。"""
    mode = ReactMode[None]()

    def thinker(goal, trace):
        return ReactDecision.finish("done", None)

    def executor(call):
        return ToolResult(call_id=call.call_id)

    with pytest.raises(ValueError, match="goal"):
        mode.run_react("   ", thinker, executor)
    with pytest.raises(ValueError, match="max_iterations"):
        mode.run_react("goal", thinker, executor, max_iterations=0)
    with pytest.raises(TypeError, match="executor"):
        mode.run_react("goal", thinker, object())


def test_react_mode_rejects_non_decision_output() -> None:
    """思考器返回非 ReactDecision 时应生成失败结果。"""
    result = ReactMode[None]().run_react(
        "分析任务",
        lambda goal, trace: "invalid decision",
        lambda call: ToolResult(call_id=call.call_id),
    )

    assert result.status is ReactStatus.Failed
    assert "ReactDecision" in result.error


def test_react_mode_rejects_mismatched_tool_result_call_id() -> None:
    """工具结果关联到其他调用时应转为失败观察，防止结果串线。"""
    call = ToolCall(call_id="expected-call", name="scan")

    result = ReactMode[None]().run_react(
        "验证调用关联",
        lambda goal, trace: ReactDecision.act("执行扫描", call),
        lambda action: ToolResult(call_id="another-call", output={"ports": [22]}),
        stop_on_tool_error=True,
    )

    assert result.status is ReactStatus.Failed
    assert len(result.steps) == 1
    observation = result.steps[0].observation
    assert observation.call_id == "expected-call"
    assert observation.ok is False
    assert observation.meta["exception_type"] == "ValueError"
    assert "does not match" in observation.error


def test_react_mode_rejects_non_tool_result_from_executor() -> None:
    """执行器返回裸字典时应形成可审计失败，而不是污染后续思考。"""
    result = ReactMode[None]().run_react(
        "验证执行器契约",
        lambda goal, trace: ReactDecision.act("调用工具", ToolCall(name="lookup")),
        lambda action: {"ok": True},
        stop_on_tool_error=True,
    )

    assert result.status is ReactStatus.Failed
    assert len(result.steps) == 1
    observation = result.steps[0].observation
    assert observation.ok is False
    assert observation.meta["exception_type"] == "TypeError"
    assert "ToolResult" in observation.error


def test_react_mode_preserves_trace_when_later_thinking_fails() -> None:
    """获得观察后的下一轮思考失败时应保留此前的完整工具轨迹。"""

    def thinker(goal, trace):
        if not trace:
            return ReactDecision.act("先获取证据", ToolCall(name="collect"))
        raise RuntimeError("model unavailable after observation")

    result = ReactMode[None]().run_react(
        "收集并分析证据",
        thinker,
        lambda action: ToolResult(call_id=action.call_id, output={"artifact": "auth.log"}),
    )

    assert result.status is ReactStatus.Failed
    assert len(result.steps) == 1
    assert result.steps[0].observation.output == {"artifact": "auth.log"}
    assert result.final_thought == "先获取证据"
    assert "model unavailable after observation" in result.error
