# date: 2026-08-12
# dev: overwhelmingly
"""ReAct 推理模式——可追溯的 think→act→observe 工具调用循环。

本模块只负责编排推理循环，不直接调用 LLM、系统命令或网络工具。调用方注入
思考器与受控工具执行器，使同一循环既能在测试中使用 Mock，也能在后续 AP2
Agent 接入时复用沙箱 ``ExecutionAPI``。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Generic, TypeAlias, TypeVar

from aegisos_agents.api import ExecutionAPI
from protocol.tool import ToolCall, ToolResult

OutputT = TypeVar("OutputT")


class ReactDecisionKind(StrEnum):
    """思考阶段允许产生的两类决策。"""

    Act = "act"
    Finish = "finish"


class ReactStatus(StrEnum):
    """ReAct 循环的终态。"""

    Succeeded = "succeeded"
    Failed = "failed"
    MaxIterations = "max_iterations"


@dataclass(frozen=True)
class ReactDecision(Generic[OutputT]):
    """思考器在一轮推理后给出的结构化决策。

    Attributes:
        kind: 决策类型；调用工具或返回最终结果。
        thought: 本轮推理摘要，用于审计和回放，不应包含敏感凭据。
        action: ``Act`` 决策对应的工具调用。
        final_output: ``Finish`` 决策对应的最终输出。
    """

    kind: ReactDecisionKind
    thought: str
    action: ToolCall | None = None
    final_output: OutputT | None = None

    def __post_init__(self) -> None:
        """校验决策类型与载荷是否一致。"""
        if self.kind is ReactDecisionKind.Act and self.action is None:
            raise ValueError("Act decision requires a ToolCall action")
        if self.kind is ReactDecisionKind.Finish and self.action is not None:
            raise ValueError("Finish decision cannot include a ToolCall action")

    @classmethod
    def act(cls, thought: str, action: ToolCall) -> ReactDecision[OutputT]:
        """创建工具调用决策。

        Args:
            thought: 选择该工具的推理摘要。
            action: 待执行的强类型工具调用。

        Returns:
            ``Act`` 类型决策。
        """
        return cls(kind=ReactDecisionKind.Act, thought=thought, action=action)

    @classmethod
    def finish(
        cls,
        thought: str,
        final_output: OutputT | None,
    ) -> ReactDecision[OutputT]:
        """创建循环结束决策。

        Args:
            thought: 结束循环的推理摘要。
            final_output: 最终结构化输出。

        Returns:
            ``Finish`` 类型决策。
        """
        return cls(
            kind=ReactDecisionKind.Finish,
            thought=thought,
            final_output=final_output,
        )


@dataclass(frozen=True)
class ReactStep:
    """一次完整的 think→act→observe 轨迹。

    Attributes:
        iteration: 从 1 开始的循环轮次。
        thought: 本轮推理摘要。
        action: 本轮工具调用。
        observation: 工具返回的观察结果；异常也会转换为失败结果。
    """

    iteration: int
    thought: str
    action: ToolCall
    observation: ToolResult


@dataclass(frozen=True)
class ReactResult(Generic[OutputT]):
    """ReAct 循环的最终结果与可回放轨迹。

    Attributes:
        goal: 本次循环处理的目标。
        status: 循环终态。
        steps: 已执行的工具调用轨迹。
        final_output: 成功结束时的最终输出。
        final_thought: 最后一次思考摘要。
        error: 失败或达到轮数上限时的原因。
    """

    goal: str
    status: ReactStatus
    steps: list[ReactStep] = field(default_factory=list)
    final_output: OutputT | None = None
    final_thought: str = ""
    error: str = ""

    @property
    def succeeded(self) -> bool:
        """返回循环是否成功完成。"""
        return self.status is ReactStatus.Succeeded


ReactThinker: TypeAlias = Callable[[str, tuple[ReactStep, ...]], ReactDecision[OutputT]]
ReactExecutor: TypeAlias = ExecutionAPI | Callable[[ToolCall], ToolResult]


class ReactMode(Generic[OutputT]):
    """通用 ReAct 循环编排器。

    思考器每轮读取目标和 tuple 形式的历史轨迹，选择调用一个工具或结束循环。工具失败
    默认作为观察反馈给下一轮思考，以支持重试和备选路径；安全敏感场景可启用
    ``stop_on_tool_error`` 在首次失败后停止。
    """

    def run_react(
        self,
        goal: str,
        thinker: ReactThinker[OutputT],
        executor: ReactExecutor,
        *,
        max_iterations: int = 8,
        stop_on_tool_error: bool = False,
    ) -> ReactResult[OutputT]:
        """执行 think→act→observe 循环直到完成或达到保护条件。

        Args:
            goal: 当前任务目标。
            thinker: 思考回调，接收目标与只读历史并返回 ``ReactDecision``。
            executor: ``ExecutionAPI`` 实例或兼容的工具执行函数。
            max_iterations: 最大推理/工具调用轮数，必须大于 0。
            stop_on_tool_error: 是否在首个失败观察后立即终止。

        Returns:
            包含终态、最终输出和完整轨迹的 ``ReactResult``。

        Raises:
            ValueError: 当目标为空或最大轮数不合法时。
            TypeError: 当执行器既不可调用也未实现 ``execute`` 时。
        """
        if not goal.strip():
            raise ValueError("goal must not be empty")
        if max_iterations <= 0:
            raise ValueError("max_iterations must be greater than zero")
        if not callable(executor) and not callable(getattr(executor, "execute", None)):
            raise TypeError("executor must be callable or implement execute(ToolCall)")

        steps: list[ReactStep] = []
        last_thought = ""

        for iteration in range(1, max_iterations + 1):
            try:
                # tuple 防止思考器增删既有轨迹，保证回放顺序稳定。
                decision = thinker(goal, tuple(steps))
            except Exception as exc:
                return ReactResult(
                    goal=goal,
                    status=ReactStatus.Failed,
                    steps=steps,
                    final_thought=last_thought,
                    error=f"think failed: {type(exc).__name__}: {exc}",
                )

            if not isinstance(decision, ReactDecision):
                return ReactResult(
                    goal=goal,
                    status=ReactStatus.Failed,
                    steps=steps,
                    final_thought=last_thought,
                    error="thinker must return ReactDecision",
                )

            last_thought = decision.thought
            if decision.kind is ReactDecisionKind.Finish:
                return ReactResult(
                    goal=goal,
                    status=ReactStatus.Succeeded,
                    steps=steps,
                    final_output=decision.final_output,
                    final_thought=decision.thought,
                )

            # ReactDecision 自身已校验 Act 必须包含 action，此断言收窄静态类型。
            action = decision.action
            assert action is not None
            observation = self._execute_action(executor, action)
            steps.append(
                ReactStep(
                    iteration=iteration,
                    thought=decision.thought,
                    action=action,
                    observation=observation,
                )
            )

            if stop_on_tool_error and not observation.ok:
                return ReactResult(
                    goal=goal,
                    status=ReactStatus.Failed,
                    steps=steps,
                    final_thought=decision.thought,
                    error=observation.error or f"tool {action.name!r} failed",
                )

        return ReactResult(
            goal=goal,
            status=ReactStatus.MaxIterations,
            steps=steps,
            final_thought=last_thought,
            error=f"ReAct loop reached max_iterations={max_iterations}",
        )

    @staticmethod
    def _execute_action(executor: ReactExecutor, action: ToolCall) -> ToolResult:
        """执行工具并把执行异常规范化为失败观察。"""
        try:
            result = executor(action) if callable(executor) else executor.execute(action)

            if not isinstance(result, ToolResult):
                raise TypeError("executor must return ToolResult")
            if result.call_id and result.call_id != action.call_id:
                raise ValueError(
                    f"ToolResult call_id {result.call_id!r} does not match {action.call_id!r}"
                )
            if not result.call_id:
                # 部分轻量执行器省略 call_id；补齐后才能可靠关联 action/observation。
                result = replace(result, call_id=action.call_id)
            return result
        except Exception as exc:
            return ToolResult(
                call_id=action.call_id,
                ok=False,
                error=str(exc),
                meta={"exception_type": type(exc).__name__},
            )


__all__ = [
    "ReactDecision",
    "ReactDecisionKind",
    "ReactExecutor",
    "ReactMode",
    "ReactResult",
    "ReactStatus",
    "ReactStep",
    "ReactThinker",
]
