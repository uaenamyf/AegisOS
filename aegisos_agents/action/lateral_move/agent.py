# date: 2026-07-06
# dev: myf
"""红队横向移动 Agent 模块（SDK 结构化输出版）。

本模块接收已有的攻击利用链和网络拓扑图，利用大语言模型规划
从已攻陷资产向更多内部资产横向移动的路径，输出额外的攻击步骤
（``AttackStep``）列表。SDK 的 ``output_type`` 结构化输出自动处理
JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""
from __future__ import annotations

import json

from aegisos_agents.action.output_types import LateralMoveResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import AttackChain, AttackStep
from protocol.graph import Graph

SYSTEM_PROMPT = (
    "You are a lateral movement planner. Given an attack chain and network "
    "topology, return JSON with a 'steps' array. Each step has: step_id, "
    "technique (ATT&CK id), from_asset, to_asset, success."
)


class LateralMoveAgent(StructuredAgent[LateralMoveResult]):
    """红队横向移动 Agent（SDK 结构化输出）。

    根据已有攻击链和当前网络拓扑，利用大语言模型规划从已攻陷
    资产向其他内部资产横向移动的攻击步骤。SDK 的 ``output_type``
    机制自动将返回 JSON 解析为 :class:`LateralMoveResult`
    （Pydantic 验证 + 自动重试），再转为 ``AttackStep`` 列表返回。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`LateralMoveResult`。
        TEMPERATURE: 采样温度，0.4 鼓励多路径探索。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = LateralMoveResult
    TEMPERATURE = 0.4

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化横向移动 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``LateralMoveAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def plan_moves(self, chain: AttackChain, topology: Graph) -> list[AttackStep]:
        """根据攻击链和网络拓扑规划横向移动步骤。

        将攻击链信息和拓扑节点信息序列化为 JSON 交给 LLM，SDK 自动
        处理 JSON 解析与 Pydantic 验证，最终将 :class:`AttackStepModel`
        转为 ``AttackStep``（protocol dataclass）返回，保持接口兼容。

        Args:
            chain: 当前攻击利用链（含已有步骤）。
            topology: 网络拓扑图（含节点信息）。

        Returns:
            规划出的横向移动步骤列表；LLM 失败时返回空列表。
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
        topo_nodes = [
            {"node_id": n.node_id, "name": n.name} for n in topology.nodes.values()
        ]  # 提取拓扑节点
        result = self._run(
            f"Plan lateral moves. Chain: {chain_desc}. Topology: {json.dumps(topo_nodes)}"
        )
        # Pydantic Model → protocol dataclass 转换
        return [
            AttackStep(
                step_id=s.step_id,
                technique=s.technique,
                from_asset=s.from_asset,
                to_asset=s.to_asset,
                success=s.success,
            )
            for s in result.steps
        ]
