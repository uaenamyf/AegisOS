# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 红队侦察 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Asset

"""红队侦察 Agent 模块。

本模块负责对目标网络范围进行侦察扫描，识别存活资产及其暴露面信息
（主机、开放服务、操作系统、暴露级别），为后续漏洞关联和利用链规划
提供基础资产清单。
"""

SYSTEM_PROMPT = (
    "You are a network reconnaissance agent. Given a target range, "
    "return a JSON object with an 'assets' array. Each asset has "
    "asset_id, host, services (list), os, exposure."
)


class ReconAgent:
    """红队侦察 Agent。

    利用大语言模型对目标网络范围进行资产发现与暴露面分析，
    将模型返回的 JSON 结果解析为 ``Asset`` 列表。
    """

    def __init__(self, provider: ModelProvider):
        """初始化侦察 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def scan(self, target_range: str) -> list[Asset]:
        """对目标网络范围执行侦察扫描，返回发现的资产列表。

        向 LLM 发送目标范围，模型返回 JSON 格式的资产清单后，
        解析为 ``Asset`` 对象列表。若模型调用失败或 JSON 解析
        失败，返回空列表。

        Args:
            target_range: 目标网络范围描述，例如 ``"192.168.1.0/24"``。

        Returns:
            发现的资产列表；调用失败或解析异常时返回空列表。
        """
        prompt = f"Scan target range: {target_range}"
        resp = self._provider.complete(
            LLMRequest(
                prompt=prompt,
                model_id="recon-agent",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,  # 较低温度保证侦察结果稳定
            )
        )
        if not resp.ok:
            return []  # 模型调用失败，返回空列表
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            return [
                Asset(
                    asset_id=a.get("asset_id", ""),
                    host=a.get("host", ""),
                    services=a.get("services", []),
                    os=a.get("os", ""),
                    exposure=a.get("exposure", "external"),  # 默认暴露级别为 external
                )
                for a in data.get("assets", [])  # 遍历 assets 数组
            ]
        except (json.JSONDecodeError, KeyError):
            return []  # JSON 解析失败或字段缺失，返回空列表
