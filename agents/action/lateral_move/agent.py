# @aegis-gen
# date: 2026-07-04
# dev: Claude Code (glm-5.2)
# change: 红队横向移动 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph

SYSTEM_PROMPT = (
    "You are a lateral movement planner. Given an attack chain and network "
    "topology, return JSON with a 'steps' array. Each step has: step_id, "
    "technique (ATT&CK id), from_asset, to_asset, success."
)


class LateralMoveAgent:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    def plan_moves(self, chain: AttackChain, topology: Graph) -> list[AttackStep]:
        chain_desc = json.dumps(
            {
                "chain_id": chain.chain_id,
                "target": chain.target,
                "current_steps": [
                    {"step_id": s.step_id, "to_asset": s.to_asset} for s in chain.steps
                ],
            }
        )
        topo_nodes = [{"node_id": n.node_id, "name": n.name} for n in topology.nodes.values()]
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Plan lateral moves. Chain: {chain_desc}. Topology: {json.dumps(topo_nodes)}",
                model_id="lateral-move",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.4,
            )
        )
        if not resp.ok:
            return []
        try:
            data = json.loads(resp.text)
            return [
                AttackStep(
                    step_id=s.get("step_id", ""),
                    technique=s.get("technique", ""),
                    from_asset=s.get("from_asset", ""),
                    to_asset=s.get("to_asset", ""),
                    success=s.get("success", False),
                )
                for s in data.get("steps", [])
            ]
        except (json.JSONDecodeError, KeyError):
            return []
