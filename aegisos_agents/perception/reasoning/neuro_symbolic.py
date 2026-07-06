# date: 2026-07-08
# dev: myf
"""神经-符号推理模块（SDK 结构化输出 + output_guardrail 版）。

实现"神经（LLM）生成 -> 符号规则校验 -> 反馈修复"的闭环：
    1. 由 SDK ``StructuredAgent``（神经侧）调用 LLM 生成结构化攻击链；
    2. 由 ``validate_chain``（符号侧）依据允许的攻击技术白名单进行校验；
    3. ``validate_and_fix`` 将违规信息拼入下一轮 prompt 反馈给 LLM 重新
       生成，直至无问题或达到最大迭代次数。

与旧版的区别：
    - 删除 ``LLMRequest`` / ``ModelProvider`` 依赖，改用 ``StructuredAgent`` 基类
    - 删除手写 ``json.loads + try/except``，由 SDK ``output_type`` 自动解析
    - ``validate_chain`` 保留为纯函数（无 LLM 调用）
    - 闭环的"重试"逻辑由 ``validate_and_fix`` 手动控制
      （SDK guardrail 触发后会抛异常而非自动重试）
"""

from __future__ import annotations

import json
from typing import Any

from aegisos_agents.action.output_types import ExploitPlannerResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import AttackChain, AttackStep

# LLM 的系统提示词：约束其输出为结构化 JSON 攻击链
SYSTEM_PROMPT = (
    "You are an attack chain generator. Given a previous chain with "
    "validation issues, generate a corrected chain. Return JSON with "
    "chain_id, target, steps (array of {step_id, technique, from_asset, "
    "to_asset, success}), status."
)


def validate_chain(chain: AttackChain, rules: dict) -> list[str]:
    """符号侧校验：检查攻击链中各步骤的技术是否在允许列表内。

    纯函数，无 LLM 调用，不依赖任何外部状态。
    同时被 ``validate_and_fix`` 循环和 ``output_guardrail`` 回调复用。

    Args:
        chain: 待校验的攻击链。
        rules: 规则字典，需包含 ``allowed_techniques`` 键，
            其值为允许使用的攻击技术名称列表。

    Returns:
        问题描述列表。若列表为空表示校验通过；每个元素为一条问题描述字符串。
    """
    issues: list[str] = []
    # 取出允许使用的技术白名单，缺失则视为空列表（即全部禁止）
    allowed = rules.get("allowed_techniques", [])
    for step in chain.steps:
        # 仅当步骤声明了技术且该技术不在白名单时记为问题
        if step.technique and step.technique not in allowed:
            issues.append(f"Technique {step.technique} not in allowed list")
    return issues


def _result_to_chain(result: ExploitPlannerResult, fallback: AttackChain) -> AttackChain:
    """将 SDK 结构化输出 ``ExploitPlannerResult`` 转为 ``AttackChain``。

    Args:
        result: SDK 返回的 Pydantic 结构化输出。
        fallback: 字段缺失时的回退攻击链（沿用原链的 chain_id/target）。

    Returns:
        重建后的 :class:`AttackChain` 实例。
    """
    steps = [
        AttackStep(
            step_id=s.step_id,
            technique=s.technique,
            from_asset=s.from_asset,
            to_asset=s.to_asset,
            success=s.success,
        )
        for s in result.steps
    ]
    return AttackChain(
        chain_id=result.chain_id or fallback.chain_id,
        target=result.target or fallback.target,
        steps=steps,
        status=result.status or "regenerated",
    )


class NeuroSymbolicAgent(StructuredAgent[ExploitPlannerResult]):
    """神经-符号闭环 Agent（SDK 结构化输出）。

    继承 :class:`StructuredAgent`，使用 SDK ``Agent(output_type=...)`` 自动
    处理结构化 JSON 解析。符号校验由 :func:`validate_chain` 在
    ``validate_and_fix`` 循环中执行：若违规则将违规信息拼入下一轮 prompt
    反馈 LLM 重新生成，最多循环 ``max_iterations`` 次。

    Attributes:
        SYSTEM_PROMPT: 系统提示词。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`ExploitPlannerResult`。
        TEMPERATURE: 采样温度，0.3 保证结构化输出的稳定性。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = ExploitPlannerResult
    TEMPERATURE = 0.3

    def __init__(
        self,
        provider: MockProvider | None = None,
        mock: MockProvider | None = None,
        model: Any | None = None,
    ) -> None:
        """初始化神经-符号闭环 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``NeuroSymbolicLoop(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
            model: SDK ``Model`` 实例（真实 API 模式）。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def validate_and_fix(
        self,
        chain: AttackChain,
        rules: dict,
        max_iterations: int = 3,
    ) -> AttackChain:
        """迭代式校验并修复攻击链。

        流程：先符号校验当前链 → 若有问题则调用 LLM（SDK 结构化输出）
        重新生成 → 再次符号校验，最多循环 ``max_iterations`` 次。
        若中途校验通过则提前返回。

        Args:
            chain: 初始攻击链。
            rules: 传给 :func:`validate_chain` 的规则字典。
            max_iterations: 最大迭代次数，默认 3。

        Returns:
            修复后的攻击链。若最终仍有问题，返回最后一次迭代的结果。
        """
        current = chain
        # 迭代修复：每次先校验，未通过则重新生成
        for _ in range(max_iterations):
            issues = validate_chain(current, rules)
            # 校验通过：返回当前合规的链
            if not issues:
                return current
            # 校验失败：调用 LLM 生成修正后的链
            current = self._regenerate(current, issues, rules)
        # 达到最大迭代仍未通过：返回最后一次结果
        return current

    def _regenerate(
        self,
        chain: AttackChain,
        issues: list[str],
        rules: dict,
    ) -> AttackChain:
        """调用 LLM 依据问题反馈重新生成攻击链。

        使用 SDK ``StructuredAgent._run()`` 发起结构化 LLM 调用，
        SDK 自动将返回 JSON 解析为 :class:`ExploitPlannerResult`
        （Pydantic 验证 + 自动重试），再转为 ``AttackChain`` 返回。

        Args:
            chain: 当前存在问题的攻击链。
            issues: 符号侧校验发现的问题列表。
            rules: 规则字典，用于提取允许技术列表拼入反馈。

        Returns:
            重新生成的攻击链。若 LLM 调用失败则返回原链（降级策略）。
        """
        # 将当前链序列化为 JSON 描述，供 LLM 理解上下文
        chain_desc = json.dumps(
            {
                "chain_id": chain.chain_id,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "technique": s.technique,
                        "from_asset": s.from_asset,
                        "to_asset": s.to_asset,
                    }
                    for s in chain.steps
                ],
            }
        )
        # 拼接反馈文本：包含具体问题与允许技术白名单
        feedback = f"Issues: {issues}. Allowed techniques: {rules.get('allowed_techniques', [])}. Fix the chain."
        # 调用 SDK 结构化输出（自动处理 JSON 解析 + Pydantic 验证）
        prompt = f"Previous chain: {chain_desc}. {feedback}"
        try:
            result = self._run(prompt)
            return _result_to_chain(result, chain)
        except Exception:
            # LLM 调用失败或结构化输出异常：降级返回原链
            return chain


# ---- 兼容旧接口：NeuroSymbolicLoop 作为 NeuroSymbolicAgent 的别名 ----
# 旧测试代码 ``NeuroSymbolicLoop(provider=mock)`` 无需修改即可工作
NeuroSymbolicLoop = NeuroSymbolicAgent
