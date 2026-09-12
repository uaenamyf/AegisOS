# date: 2026-07-06
# dev: myf
# changelog: AP1.3 接入 Plan 范式——新增 plan_response_with_strategy 方法
# changelog: AP4.2 接入 Ask 范式——继承 AskMode，新增 plan_response_with_human_check（破坏性操作前确认 + 超时降级）
"""蓝队响应规划 Agent 模块（SDK 结构化输出版 + Plan 范式 + Ask 范式）。

AP1.3 新增：``plan_response_with_strategy`` 方法用 :class:`PlanMode` 两阶段推理，
先规划多阶段响应策略（隔离→阻断→诱饵→监控），再按策略生成详细 DefenseAction 列表。
AP4.2 新增：``plan_response_with_human_check`` 在计划含 ``isolate``/``block`` 等
破坏性动作时暂停向人类确认，超时/否认则降级为仅 ``monitor``。
原有 ``plan_response`` / ``plan_response_with_strategy`` 方法保持不变（向后兼容）。
"""
from __future__ import annotations

import json

from aegisos_agents.action.output_types import IRPlannerResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import (
    AskMode,
    AskResponse,
    AutoAskHandler,
    PlanMode,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import DefenseAction, ResponsePlan

SYSTEM_PROMPT = (
    "You are an incident response planner. Given threat hypotheses, "
    "return JSON with plan_id, actions (array of {action_id, kind "
    "isolate|block|decoy|monitor, target, rationale}), confidence (float), "
    "rollback (dict with enabled and steps)."
)

# 破坏性响应动作：会切断连接/隔离资产，执行前必须人工确认
_DESTRUCTIVE_KINDS = {"isolate", "block"}


class IRPlannerAgent(
    StructuredAgent[IRPlannerResult], PlanMode[IRPlannerResult], AskMode
):
    """蓝队响应规划 Agent（SDK 结构化输出 + Plan 范式 + Ask 范式）。

    AP1.3：``plan_response_with_strategy`` 用 :class:`PlanMode` 两阶段推理，
    先规划多阶段响应策略（隔离→阻断→诱饵→监控），再按策略生成详细 DefenseAction 列表。
    AP4.2：``plan_response_with_human_check`` 在含破坏性动作时暂停向人类确认。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = IRPlannerResult
    TEMPERATURE = 0.3

    def __init__(
        self,
        provider=None,
        mock: MockProvider | None = None,
        model=None,
        ask_handler=None,
    ) -> None:
        """初始化响应规划 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``IRPlannerAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
            model: SDK ``Model`` 实例（真实 API 模式）。
            ask_handler: 可选 :class:`AskHandler`（人机协同）；None 时退化为
                :class:`AutoAskHandler`（无人值守即时安全降级）。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)
        # AP4.2: 注入 Ask handler（无人值守时 AutoAskHandler 即时降级）
        self._ask_handler = ask_handler or AutoAskHandler()

    def plan_response(self, hypotheses: list[dict]) -> ResponsePlan:
        """根据威胁狩猎假设生成事件响应计划。

        将假设列表直接序列化为 JSON 交给 LLM，SDK 自动处理 JSON 解析与
        Pydantic 验证，最终将 :class:`IRPlannerResult` 转为 ``ResponsePlan``
        （protocol dataclass）返回。actions 转为 dict 列表以保持与原接口
        兼容（调用方按 dict 方式访问动作字段）。

        Args:
            hypotheses: 威胁狩猎假设列表，每条为包含 hypothesis/confidence/technique 的 dict。

        Returns:
            规划出的响应计划；LLM 失败时返回默认空计划。
        """
        result = self._run(f"Plan response for: {json.dumps(hypotheses)}")
        # R1.6: DefenseActionModel → protocol.cyber.DefenseAction（Pydantic 自动校验）
        return ResponsePlan(
            plan_id=result.plan_id,
            actions=[
                DefenseAction.model_validate(a.model_dump())
                for a in result.actions
            ],
            confidence=result.confidence,
            rollback=result.rollback,
        )

    def plan_response_with_strategy(self, hypotheses: list[dict]) -> ResponsePlan:
        """Plan 范式规划响应计划（AP1.3）。

        两阶段推理：
            1. 规划阶段：LLM 分析威胁假设，生成多阶段响应策略（隔离→阻断→诱饵→监控）。
            2. 执行阶段：按策略生成详细 DefenseAction 列表 + 置信度 + 回滚方案。

        与 :meth:`plan_response` 的区别：先规划再执行，响应计划更系统化。
        规划阶段失败时降级到直接 :meth:`plan_response`。

        Args:
            hypotheses: 威胁狩猎假设列表。

        Returns:
            规划出的响应计划（``ResponsePlan``）。
        """
        prompt = f"Plan response for: {json.dumps(hypotheses)}"
        result = self._run_with_plan(prompt, domain="incident_response")
        # R1.6: DefenseActionModel → protocol.cyber.DefenseAction（Pydantic 自动校验）
        return ResponsePlan(
            plan_id=result.plan_id,
            actions=[
                DefenseAction.model_validate(a.model_dump())
                for a in result.actions
            ],
            confidence=result.confidence,
            rollback=result.rollback,
        )

    # date: 2026-08-17
    # dev: 陈子毅
    # changelog: AP4.2 新增 plan_response_with_human_check——破坏性动作前暂停确认，超时降级为仅 monitor
    def plan_response_with_human_check(
        self,
        hypotheses: list[dict],
        ask_handler=None,
    ) -> ResponsePlan:
        """带人工确认的响应计划（AP4 人机协同）。

        先按既有逻辑生成响应计划，再检查是否含 ``isolate``/``block`` 等
        破坏性动作：若有，暂停向人类提问确认；超时或否认则降级为仅
        ``monitor``，确保不擅自执行破坏性操作。

        与 :meth:`plan_response` 的区别：在破坏性动作前插入人工确认闸门，
        无人值守/超时自动走保守降级，不影响整体攻防链推进。

        Args:
            hypotheses: 威胁狩猎假设列表。
            ask_handler: 可选 :class:`AskHandler`；None 时使用实例注入的 handler。

        Returns:
            响应计划（``ResponsePlan``）；含破坏性动作时被人类确认/降级后的版本。
        """
        # 先生成基础计划（复用既有 LLM 调用路径）
        plan = self.plan_response(hypotheses)

        # R1.6: DefenseAction Pydantic 模型，用属性访问替代 dict.get
        destructive = [
            a for a in plan.actions if (a.kind in _DESTRUCTIVE_KINDS)
        ]
        if not destructive:
            # 无破坏性动作：直接返回，无需暂停
            return plan

        # 设置本次使用的 handler（优先参数，其次实例注入）
        if ask_handler is not None:
            self.set_ask_handler(ask_handler)

        response = self.ask_human(
            question="响应计划包含破坏性动作（隔离/阻断），是否执行？",
            options=["确认执行", "降级为仅监控", "取消执行"],
            context={
                "plan_id": plan.plan_id,
                "destructive_actions": [a.action_id for a in destructive],
                "confidence": plan.confidence,
            },
            # 无人值守/超时：保守降级为仅 monitor（不执行破坏性动作）
            on_timeout=lambda req: AskResponse(
                answered=False,
                answer="降级为仅监控",
                timeout=True,
                rationale="无人值守超时，保守降级为仅 monitor",
            ),
        )

        answer = response.answer
        if answer == "确认执行":
            return plan
        if answer == "取消执行":
            # 人类取消：返回空动作的安全计划
            return ResponsePlan(
                plan_id=plan.plan_id,
                actions=[],
                confidence=plan.confidence,
                rollback=plan.rollback,
            )
        # 降级为仅 monitor / 超时默认：破坏性动作转换为 monitor
        from protocol.cyber import DefenseAction
        new_actions = []
        for a in plan.actions:
            if a.kind in _DESTRUCTIVE_KINDS:
                new_actions.append(
                    DefenseAction(
                        action_id=a.action_id,
                        kind="monitor",
                        target=a.target,
                        rationale=f"degraded from {a.kind} to monitor-only (human/timeout)",
                    )
                )
            else:
                new_actions.append(a)
        return ResponsePlan(
            plan_id=plan.plan_id,
            actions=new_actions,
            confidence=plan.confidence,
            rollback=plan.rollback,
        )
