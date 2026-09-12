# date: 2026-07-07
# dev: myf
# changelog: AP1.1 新建 Plan 行动模式——两阶段 prompt（先规划策略，再按策略生成详细产出）
"""Plan 行动模式 —— 两阶段 LLM 推理增强。

本模块实现 :class:`PlanMode`，将单次 LLM 调用拆分为两阶段：
    1. **规划阶段**：LLM 分析任务目标与输入，生成高层策略 + 步骤分解
       （输出 :class:`PlanResult`，含 strategy + steps）。
    2. **执行阶段**：将策略与原始输入一并交给 Agent，按策略逐步生成
       详细产出（输出 Agent 原有 output_type）。

设计动机：
    - 单次 LLM 调用容易跳过深思直接产出，复杂任务质量不稳定。
    - 先规划再执行可显著提升 AttackChain / ResponsePlan / LateralMove
      等多步骤产出的连贯性与完整性。
    - 纯 LLM 推理增强，不依赖 Docker 沙箱，可独立实现（AP1 范畴）。

与 :class:`StructuredAgent` 的关系：
    - PlanMode 是混入（mixin）能力，不替代 StructuredAgent 继承链。
    - Agent 通过调用 :meth:`PlanMode._run_with_plan` 方法获得 Plan 范式能力，
      原有 :meth:`StructuredAgent._run` 保持不变（向后兼容）。
    - Plan 阶段复用一个独立的 SDK ``Agent(output_type=PlanResult)``，
      执行阶段用 Agent 自身的 ``_sdk_agent``。

使用方式（以 ExploitPlannerAgent 为例）::

    class ExploitPlannerAgent(StructuredAgent[ExploitPlannerResult], PlanMode):
        ...
        def plan_with_strategy(self, findings):
            prompt = f"Plan exploit chain for: {json.dumps(findings)}"
            result = self._run_with_plan(prompt, domain="exploit_planning")
            return self._result_to_chain(result)

Attributes:
    PlanResult: 规划阶段的 Pydantic 输出类型（strategy + steps）。
    PlanMode:混入类，提供 ``_run_with_plan`` 方法。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from agents import Agent, AgentOutputSchema, ModelSettings
from pydantic import BaseModel, Field

from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider

T = TypeVar("T", bound=BaseModel)


class PlanStep(BaseModel):
    """规划阶段的单个步骤描述。

    Attributes:
        step_id: 步骤标识（如 ``"step-1"``）。
        description: 步骤描述（如 ``"利用 SSH 弱口令进入 asset-1"``）。
        rationale: 选择该步骤的理由（如 ``"SSH 暴露且 CVSS 8.1"``）。
    """

    step_id: str = ""
    description: str = ""
    rationale: str = ""


class PlanResult(BaseModel):
    """规划阶段的 Pydantic 输出类型（阶段 1 产出）。

    Attributes:
        strategy: 高层策略概述（如 ``"从外网入口资产横向到内网核心"``）。
        steps: 步骤分解列表，每步含描述与理由。
        risks: 风险点列表（如 ``["可能触发 IDS", "需要凭据"]``）。
    """

    strategy: str = ""
    steps: list[PlanStep] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# 规划阶段的系统提示词（通用，按 domain 动态注入角色描述）
_PLAN_SYSTEM_PROMPT = (
    "You are a strategic planner. Given a task description and input context, "
    "analyze the goal and produce a high-level strategy with step-by-step "
    "decomposition. Return JSON with: strategy (string), steps (array of "
    "{step_id, description, rationale}), risks (array of strings). "
    "Be specific and actionable; each step should correspond to one concrete "
    "action the downstream executor will take."
)


class PlanMode(Generic[T]):
    """Plan 行动模式混入 —— 为 :class:`StructuredAgent` 子类提供两阶段推理能力。

    子类继承 ``StructuredAgent[T]`` 与 ``PlanMode[T]`` 后，调用
    :meth:`_run_with_plan` 即可用 Plan 范式执行：先规划策略，再按策略
    生成详细产出。

    工作流程：
        1. 构造独立的规划 SDK ``Agent(output_type=PlanResult)``。
        2. 用 ``Runner.run_sync`` 调规划 Agent，拿到 :class:`PlanResult`。
        3. 把策略 + 步骤 + 原始 prompt 拼成增强 prompt。
        4. 调用 :meth:`StructuredAgent._run` 用 Agent 自身 output_type 生成详细产出。

    Attributes:
        _plan_agent: 规划阶段的 SDK ``Agent`` 实例（懒构造，首次调用时建）。
    """

    if TYPE_CHECKING:
        # Mixin 依赖宿主（StructuredAgent 子类）提供的成员；静态声明使
        # mypy 可见，运行时由宿主类真实提供。
        _model: Any

        def _run(self, prompt: str, timeout: float = 120.0) -> T: ...

    _plan_agent: Agent | None = None

    def _get_plan_agent(self) -> Agent:
        """懒构造规划 SDK Agent（首次调用时创建，复用 self 的 model）。

        Returns:
            装配好的 SDK ``Agent`` 实例，``output_type=PlanResult``。
        """
        if self._plan_agent is None:
            model: Any = self._model  # PlanMode 与 StructuredAgent 混入使用
            self._plan_agent = Agent(
                name=f"{self.__class__.__name__}_Planner",
                instructions=_PLAN_SYSTEM_PROMPT,
                output_type=AgentOutputSchema(PlanResult, strict_json_schema=False),
                model=model,
                model_settings=ModelSettings(temperature=0.2),
            )
        return self._plan_agent

    def _run_with_plan(
        self,
        prompt: str,
        domain: str = "",
        timeout: float = 120.0,
    ) -> T:
        """Plan 范式执行：先规划策略，再按策略生成详细产出。

        Args:
            prompt: 原始用户 prompt（与 :meth:`StructuredAgent._run` 相同）。
            domain: 任务域描述（如 ``"exploit_planning"``），注入规划 prompt
                帮助 LLM 理解上下文。空字符串表示不注入。
            timeout: 执行阶段超时秒数（线程池模式）。

        Returns:
            ``T`` 类型的结构化输出实例（与 :meth:`_run` 返回类型相同）。

        Raises:
            RuntimeError: 规划阶段失败时降级到直接 ``_run``，不抛异常。
        """
        # 阶段 1：规划策略
        try:
            from agents import Runner

            plan_agent = self._get_plan_agent()
            domain_hint = f"[Domain: {domain}] " if domain else ""
            plan_prompt = f"{domain_hint}Analyze and plan for: {prompt}"
            plan_result = Runner.run_sync(plan_agent, plan_prompt)
            plan: PlanResult = plan_result.final_output  # type: ignore[assignment]
            # 规划结果为空（Mock 占位或 LLM 未给策略）→ 降级到直接执行
            if not plan.strategy and not plan.steps:
                # type: ignore[attr-defined]
                return self._run(prompt, timeout=timeout)
        except Exception:
            # 规划失败：降级到直接执行（保持向后兼容，不抛异常）
            # type: ignore[attr-defined]
            return self._run(prompt, timeout=timeout)

        # 阶段 2：把策略拼入增强 prompt，按策略生成详细产出
        strategy_desc = self._format_plan(plan)
        enhanced_prompt = (
            f"Strategy: {plan.strategy}\n"
            f"Planned steps:\n{strategy_desc}\n"
            f"Risks to consider: {', '.join(plan.risks) if plan.risks else 'none'}\n"
            f"Now execute the task following this strategy.\n"
            f"Original request: {prompt}"
        )
        # type: ignore[attr-defined]
        return self._run(enhanced_prompt, timeout=timeout)

    @staticmethod
    def _format_plan(plan: PlanResult) -> str:
        """将 PlanResult 格式化为可读的步骤列表字符串。"""
        if not plan.steps:
            return "(no specific steps planned)"
        lines = []
        for step in plan.steps:
            sid = step.step_id or "?"
            desc = step.description or "(no description)"
            rationale = f" — {step.rationale}" if step.rationale else ""
            lines.append(f"  {sid}. {desc}{rationale}")
        return "\n".join(lines)


def create_plan_mode_agent(
    agent_class: type[StructuredAgent[T]],
    mock: MockProvider | None = None,
    model: Any | None = None,
    **kwargs: Any,
) -> StructuredAgent[T] & PlanMode[T]:
    """工厂函数 —— 创建同时继承 StructuredAgent 与 PlanMode 的 Agent 实例。

    动态构造一个联合子类，让现有 Agent 类获得 ``_run_with_plan`` 能力，
    无需修改 Agent 类的继承链。

    Args:
        agent_class: 现有 Agent 类（如 ``ExploitPlannerAgent``）。
        mock: MockProvider 实例（Mock 模式）。
        model: SDK ``Model`` 实例（真实 API 模式）。
        **kwargs: 透传给 agent_class 构造函数的其他参数。

    Returns:
        同时具备 StructuredAgent 与 PlanMode 能力的 Agent 实例。
    """
    # 动态构造联合子类，避免修改现有 Agent 的继承链
    joint_name = f"{agent_class.__name__}WithPlan"
    joint_class = type(joint_name, (agent_class, PlanMode), {})
    return joint_class(mock=mock, model=model, **kwargs)  # type: ignore[call-arg]
