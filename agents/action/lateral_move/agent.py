# date: 2026-07-04
# dev: myf
# changelog: 红队横向移动 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph

"""红队横向移动 Agent 模块。

本模块接收已有的攻击利用链和网络拓扑图，利用大语言模型规划
从已攻陷资产向更多内部资产横向移动的路径，输出额外的攻击步骤
（``AttackStep``）列表。
"""

SYSTEM_PROMPT = (
    "You are a lateral movement planner. Given an attack chain and network "
    "topology, return JSON with a 'steps' array. Each step has: step_id, "
    "technique (ATT&CK id), from_asset, to_asset, success."
)


class LateralMoveAgent:
    """红队横向移动 Agent。

    根据已有攻击链和当前网络拓扑，利用大语言模型规划从已攻陷
    资产向其他内部资产横向移动的攻击步骤。
    """

    def __init__(self, provider: ModelProvider):
        """初始化横向移动 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def plan_moves(self, chain: AttackChain, topology: Graph) -> list[AttackStep]:
        """根据攻击链和网络拓扑规划横向移动步骤。

        将攻击链信息和拓扑节点信息序列化为 JSON 交给 LLM，
        模型返回 steps 数组，逐条解析为 ``AttackStep`` 对象。
        若模型调用失败或 JSON 解析失败，返回空列表。

        Args:
            chain: 当前攻击利用链（含已有步骤）。
            topology: 网络拓扑图（含节点信息）。

        Returns:
            规划出的横向移动步骤列表；调用失败或解析异常时返回空列表。
        """
        chain_desc = json.dumps(  # 序列化攻击链信息供模型理解
            {
                "chain_id": chain.chain_id,
                "target": chain.target,
                "current_steps": [
                    {"step_id": s.step_id, "to_asset": s.to_asset} for s in chain.steps
                ],
            }
        )
        topo_nodes = [{"node_id": n.node_id, "name": n.name} for n in topology.nodes.values()]  # 提取拓扑节点
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Plan lateral moves. Chain: {chain_desc}. Topology: {json.dumps(topo_nodes)}",
                model_id="lateral-move",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.4,  # 中等温度鼓励多路径探索
            )
        )
        if not resp.ok:
            return []  # 模型调用失败，返回空列表
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            return [
                AttackStep(
                    step_id=s.get("step_id", ""),
                    technique=s.get("technique", ""),
                    from_asset=s.get("from_asset", ""),
                    to_asset=s.get("to_asset", ""),
                    success=s.get("success", False),  # 默认未成功
                )
                for s in data.get("steps", [])  # 遍历 steps 数组
            ]
        except (json.JSONDecodeError, KeyError):
            return []  # JSON 解析失败或字段缺失，返回空列表
