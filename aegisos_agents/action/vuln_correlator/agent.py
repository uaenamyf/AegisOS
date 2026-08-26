# date: 2026-07-06
# dev: myf
# change: 2026-08-12 overwhelmingly — AP2.3 接入 ReAct CVE 查询工具循环
"""红队漏洞关联 Agent 模块（SDK 结构化输出版）。

本模块接收侦察阶段发现的资产清单，将其交给大语言模型进行
漏洞关联分析，输出每个资产上可能存在的漏洞信息（CVE、
CVSS 评分、攻击面），为利用链规划提供输入。SDK 的 ``output_type``
结构化输出自动处理 JSON 解析与 Pydantic 验证，无需手写
``json.loads + try/except``。
"""

from __future__ import annotations

import json

from aegisos_agents.action.output_types import VulnCorrelatorResult
from aegisos_agents.action.react_support import render_tool_output, run_tool_react
from aegisos_agents.action.structured_agent import StructuredAgent
from aegisos_agents.perception.reasoning.strategies import (
    ReactExecutor,
    ReactResult,
    ReactThinker,
)
from aegisos_agents.tools.llms.mock_provider import MockProvider
from protocol.cyber import Asset, VulnFinding
from protocol.tool import ToolCall, ToolResult

SYSTEM_PROMPT = (
    "You are a vulnerability correlation agent. Given a list of assets, "
    "return JSON with a 'findings' array. Each finding has: finding_id, "
    "cve_id, asset_id, cvss (float), attack_surface."
)


class VulnCorrelatorAgent(StructuredAgent[VulnCorrelatorResult]):
    """红队漏洞关联 Agent（SDK 结构化输出）。

    接收资产清单，利用大语言模型推断各资产可能存在的漏洞，
    SDK 的 ``output_type`` 机制自动将返回 JSON 解析为
    :class:`VulnCorrelatorResult`（Pydantic 验证 + 自动重试），
    再转为 ``VulnFinding`` 列表返回。

    Attributes:
        SYSTEM_PROMPT: 系统提示词，描述 Agent 角色与输出格式。
        OUTPUT_TYPE: SDK 结构化输出类型 :class:`VulnCorrelatorResult`。
        TEMPERATURE: 采样温度，0.2 保证漏洞判断的确定性。
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    OUTPUT_TYPE = VulnCorrelatorResult
    TEMPERATURE = 0.2

    def __init__(self, provider=None, mock: MockProvider | None = None, model=None) -> None:
        """初始化漏洞关联 Agent。

        兼容旧接口：接受 ``provider`` 参数（原 ``ModelProvider``）时走 Mock 路径，
        保持现有测试（``VulnCorrelatorAgent(provider=mock)``）无需改动。

        Args:
            provider: 旧版 ``ModelProvider``（MockProvider），兼容现有测试签名。
            mock: :class:`MockProvider` 实例，显式传入时用于 Mock 模式。
        """
        # provider 参数兼容：旧测试传 MockProvider，转用 mock 参数
        if provider is not None and mock is None:
            mock = provider
        super().__init__(model=model, mock=mock)

    def correlate(self, assets: list[Asset]) -> list[VulnFinding]:
        """对资产列表进行漏洞关联分析。

        将资产信息序列化为 JSON 交给 LLM，SDK 自动处理 JSON 解析与
        Pydantic 验证，最终将 :class:`VulnFindingModel` 转为
        ``VulnFinding``（protocol dataclass）返回，保持接口兼容。

        Args:
            assets: 待分析的资产列表。

        Returns:
            关联出的漏洞发现列表；LLM 失败时返回空列表。
        """
        asset_desc = json.dumps(  # 将资产列表序列化为 JSON 字符串供模型理解
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        result = self._run(f"Correlate vulnerabilities for these assets: {asset_desc}")
        # Pydantic Model → protocol dataclass 转换
        return [
            VulnFinding(
                finding_id=f.finding_id,
                cve_id=f.cve_id,
                asset_id=f.asset_id,
                cvss=f.cvss,
                attack_surface=f.attack_surface,
            )
            for f in result.findings
        ]

    def correlate_react(
        self,
        assets: list[Asset],
        executor: ReactExecutor,
        *,
        thinker: ReactThinker[list[VulnFinding]] | None = None,
        max_iterations: int = 8,
        stop_on_tool_error: bool = True,
    ) -> ReactResult[list[VulnFinding]]:
        """通过 ReAct 查询漏洞知识库，再归纳为漏洞发现。

        Args:
            assets: 需要验证漏洞的资产清单。
            executor: 执行 ``query_cve_db`` 的受控工具端口。
            thinker: 可选自定义思考器，用于多工具策略。
            max_iterations: 最大 ReAct 循环轮数。
            stop_on_tool_error: 是否在工具失败时立即停止。

        Returns:
            带完整轨迹的漏洞关联结果。
        """
        asset_payload = [
            {
                "asset_id": asset.asset_id,
                "host": asset.host,
                "services": asset.services,
                "os": asset.os,
                "exposure": asset.exposure,
            }
            for asset in assets
        ]

        def finalize(observation: ToolResult) -> list[VulnFinding]:
            result = self._run(
                "Correlate vulnerabilities for assets "
                f"{json.dumps(asset_payload)} using CVE observation: "
                f"{render_tool_output(observation.output)}"
            )
            return [
                VulnFinding(
                    finding_id=finding.finding_id,
                    cve_id=finding.cve_id,
                    asset_id=finding.asset_id,
                    cvss=finding.cvss,
                    attack_surface=finding.attack_surface,
                )
                for finding in result.findings
            ]

        return run_tool_react(
            goal=f"Correlate vulnerabilities for {len(assets)} assets",
            action=ToolCall(
                name="query_cve_db",
                args={"assets": asset_payload},
                permission="knowledge.read",
            ),
            executor=executor,
            finalizer=finalize,
            action_thought="需要查询 CVE 知识库验证资产暴露服务",
            finish_thought="CVE 查询观察已经足够形成漏洞关联结果",
            thinker=thinker,
            max_iterations=max_iterations,
            stop_on_tool_error=stop_on_tool_error,
        )
