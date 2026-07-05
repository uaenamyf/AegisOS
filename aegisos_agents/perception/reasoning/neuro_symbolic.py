# date: 2026-07-04
# dev: myf
# changelog: 神经-符号闭环
"""神经-符号推理模块。

实现"神经（LLM）生成 -> 符号规则校验 -> 反馈修复"的闭环：
    1. 由 LLM（神经侧）根据当前攻击链生成修正后的新链；
    2. 由 ``validate_chain``（符号侧）依据允许的攻击技术白名单进行校验；
    3. 若存在问题则将问题反馈给 LLM 重新生成，直至无问题或达到最大迭代次数。

该模块用于在红队/对抗场景下，保证生成的 AttackChain 符合预定义的约束规则。
"""

from __future__ import annotations

import json

from aegisos_agents.tools.llms.base import LLMRequest, ModelProvider
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


class NeuroSymbolicLoop:
    """神经-符号闭环控制器。

    通过反复调用 LLM 生成与符号校验，迭代修复攻击链中的违规技术，
    直到生成合规的攻击链或达到最大迭代次数。

    Attributes:
        _provider: 底层 LLM 提供方实例，用于发起补全请求。
    """

    def __init__(self, provider: ModelProvider):
        """初始化闭环控制器。

        Args:
            provider: LLM 提供方实例，需实现 ``complete(LLMRequest)`` 接口。
        """
        self._provider = provider

    def validate_and_fix(
        self,
        chain: AttackChain,
        rules: dict,
        max_iterations: int = 3,
    ) -> AttackChain:
        """迭代式校验并修复攻击链。

        流程：校验 -> 若有问题则调用 LLM 重新生成 -> 再次校验，
        最多循环 ``max_iterations`` 次。若中途校验通过则提前返回。

        Args:
            chain: 初始攻击链。
            rules: 传给 ``validate_chain`` 的规则字典。
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

        Args:
            chain: 当前存在问题的攻击链。
            issues: 符号侧校验发现的问题列表。
            rules: 规则字典，用于提取允许技术列表拼入反馈。

        Returns:
            重新生成的攻击链。若 LLM 调用失败或 JSON 解析失败，
            则返回原链（降级策略）。
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
        # 调用底层 LLM，使用较低温度（0.3）以获得更稳定、偏规则的结构化输出
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Previous chain: {chain_desc}. {feedback}",
                model_id="neuro-symbolic",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,
            )
        )
        # LLM 调用失败：降级返回原链
        if not resp.ok:
            return chain
        try:
            # 解析 LLM 返回的 JSON 并重建 AttackChain 对象
            data = json.loads(resp.text)
            # 逐条重建攻击步骤，缺失字段使用默认值
            steps = [
                AttackStep(
                    step_id=s.get("step_id", ""),
                    technique=s.get("technique", ""),
                    from_asset=s.get("from_asset", ""),
                    to_asset=s.get("to_asset", ""),
                    success=s.get("success", False),
                )
                for s in data.get("steps", [])
            ]
            # chain_id/target 缺失时回退到原链对应字段，status 默认标记为 regenerated
            return AttackChain(
                chain_id=data.get("chain_id", chain.chain_id),
                target=data.get("target", chain.target),
                steps=steps,
                status=data.get("status", "regenerated"),
            )
        except (json.JSONDecodeError, KeyError):
            # JSON 解析失败或字段缺失：降级返回原链，避免抛中断闭环
            return chain
