# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 神经-符号闭环
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import AttackChain, AttackStep

SYSTEM_PROMPT = (
    "You are an attack chain generator. Given a previous chain with "
    "validation issues, generate a corrected chain. Return JSON with "
    "chain_id, target, steps (array of {step_id, technique, from_asset, "
    "to_asset, success}), status."
)


def validate_chain(chain: AttackChain, rules: dict) -> list[str]:
    """Symbolic validation: check techniques against allowed list."""
    issues: list[str] = []
    allowed = rules.get("allowed_techniques", [])
    for step in chain.steps:
        if step.technique and step.technique not in allowed:
            issues.append(f"Technique {step.technique} not in allowed list")
    return issues


class NeuroSymbolicLoop:
    """Neural (LLM) generates -> Symbolic validates -> feedback -> fix loop."""

    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def validate_and_fix(
        self,
        chain: AttackChain,
        rules: dict,
        max_iterations: int = 3,
    ) -> AttackChain:
        current = chain
        for _ in range(max_iterations):
            issues = validate_chain(current, rules)
            if not issues:
                return current
            current = self._regenerate(current, issues, rules)
        return current

    def _regenerate(
        self,
        chain: AttackChain,
        issues: list[str],
        rules: dict,
    ) -> AttackChain:
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
        feedback = f"Issues: {issues}. Allowed techniques: {rules.get('allowed_techniques', [])}. Fix the chain."
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Previous chain: {chain_desc}. {feedback}",
                model_id="neuro-symbolic",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,
            )
        )
        if not resp.ok:
            return chain
        try:
            data = json.loads(resp.text)
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
            return AttackChain(
                chain_id=data.get("chain_id", chain.chain_id),
                target=data.get("target", chain.target),
                steps=steps,
                status=data.get("status", "regenerated"),
            )
        except (json.JSONDecodeError, KeyError):
            return chain
