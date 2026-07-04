# @aegis-gen
# date: 2026-07-04
# dev: myf
# change: 红队漏洞关联 Agent
from __future__ import annotations

import json

from agents.tools.llms.base import LLMRequest, ModelProvider
from protocol.cyber import Asset, VulnFinding

"""红队漏洞关联 Agent 模块。

本模块接收侦察阶段发现的资产清单，将其交给大语言模型进行
漏洞关联分析，输出每个资产上可能存在的漏洞信息（CVE、
CVSS 评分、攻击面），为利用链规划提供输入。
"""

SYSTEM_PROMPT = (
    "You are a vulnerability correlation agent. Given a list of assets, "
    "return JSON with a 'findings' array. Each finding has: finding_id, "
    "cve_id, asset_id, cvss (float), attack_surface."
)


class VulnCorrelatorAgent:
    """红队漏洞关联 Agent。

    接收资产清单，利用大语言模型推断各资产可能存在的漏洞，
    输出 ``VulnFinding`` 列表（包含 CVE、CVSS、攻击面等信息）。
    """

    def __init__(self, provider: ModelProvider):
        """初始化漏洞关联 Agent。

        Args:
            provider: LLM 模型提供者，用于发送补全请求。
        """
        self._provider = provider

    def correlate(self, assets: list[Asset]) -> list[VulnFinding]:
        """对资产列表进行漏洞关联分析。

        将资产信息序列化为 JSON 交给 LLM，模型返回 findings 数组，
        逐条解析为 ``VulnFinding`` 对象。若模型调用失败或 JSON
        解析失败，返回空列表。

        Args:
            assets: 待分析的资产列表。

        Returns:
            关联出的漏洞发现列表；调用失败或解析异常时返回空列表。
        """
        asset_desc = json.dumps(  # 将资产列表序列化为 JSON 字符串供模型理解
            [
                {"asset_id": a.asset_id, "host": a.host, "services": a.services, "os": a.os}
                for a in assets
            ]
        )
        resp = self._provider.complete(
            LLMRequest(
                prompt=f"Correlate vulnerabilities for these assets: {asset_desc}",
                model_id="vuln-correlator",
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,  # 低温度保证漏洞判断的确定性
            )
        )
        if not resp.ok:
            return []  # 模型调用失败，返回空列表
        try:
            data = json.loads(resp.text)  # 解析模型返回的 JSON
            return [
                VulnFinding(
                    finding_id=f.get("finding_id", ""),
                    cve_id=f.get("cve_id", ""),
                    asset_id=f.get("asset_id", ""),
                    cvss=f.get("cvss", 0.0),  # 默认 CVSS 为 0.0
                    attack_surface=f.get("attack_surface", ""),
                )
                for f in data.get("findings", [])  # 遍历 findings 数组
            ]
        except (json.JSONDecodeError, KeyError):
            return []  # JSON 解析失败或字段缺失，返回空列表
