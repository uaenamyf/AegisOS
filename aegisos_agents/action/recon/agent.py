# date: 2026-07-06
# dev: myf
# changelog: 迁移到 SDK 结构化输出——用 StructuredAgent + output_type 替代 json.loads+try/except（~77 行→~45 行）
# date: 2026-07-04
# dev: myf
# changelog: 红队侦察 Agent
from __future__ import annotations

from aegisos_agents.action.output_types import ReconResult
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Asset

"""红队侦察 Agent 模块（SDK 结构化输出版）。

本模块负责对目标网络范围进行侦察扫描，识别存活资产及其暴露面信息。
使用 openai-agents SDK 的 ``output_type`` 结构化输出，由 SDK 自动处理
JSON 解析与 Pydantic 验证，无需手写 ``json.loads + try/except``。
"""

SYSTEM_PROMPT = (
    "You are a network reconnaissance agent. Given a target range, "
    "return a JSON object with an 'assets' array. Each asset has "
    "asset_id, host, services (list), os, exposure."
)


class ReconAgent(StructuredAgent[ReconResult]):
    """红队侦察 Agent（SDK 结构化输出）。

    利用 LLM 对目标网络范围进行资产发现与暴露面分析，SDK 的 ``output_type``
    机制自动将返回 JSON 解析为 :class:`ReconResult`（Pydantic 验证 + 自动重试）。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`ReconResult`。
        TEMPERATURE: 采样温度，0.3 保证侦察结果稳定。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = ReconResult
    TEMPERATURE = 0.3

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化侦察 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``ReconAgent(provider=mock)``）无需改动。真实 API 模式
        通过 ``model=`` 注入 SDK ``Model``（由 :meth:`SDKProvider.get_sdk_model` 创建）。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
            model: SDK ``Model`` 实例（真实 API 模式）；非 None 时优先使用。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def scan(self, target_range: str) -> list[Asset]:
        """对目标网络范围执行侦察扫描，返回发现的资产列表。

        SDK 自动处理 LLM 调用 → JSON 解析 → Pydantic 验证，
        失败时 SDK 内部自动重试。最终将 :class:`AssetModel` 转为
        :class:`Asset`（protocol dataclass）返回，保持接口兼容。

        Args:
            target_range: 目标网络范围描述，例如 ``"192.168.1.0/24"``。

        Returns:
            发现的资产列表（``protocol.cyber.Asset``）；LLM 失败时返回空列表。
        """
        result = self._run(f"Scan target range: {target_range}")
        # Pydantic Model → protocol dataclass 转换
        return [
            Asset(
                asset_id=a.asset_id,
                host=a.host,
                services=a.services,
                os=a.os,
                exposure=a.exposure,
            )
            for a in result.assets
        ]
