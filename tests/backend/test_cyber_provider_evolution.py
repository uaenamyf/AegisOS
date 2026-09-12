# date: 2026-09-04
# dev: AegisOS
# changelog: R1.5 新增——CyberMockProvider 按轮演化单测

"""R1.5：`_CyberMockProvider` 按轮演化单测。

验证多轮收敛攻防演练所依赖的"轮次上下文"：
    - round>=2 时侦察才暴露新资产 asset-3；
    - round>=2 时利用链才新增 step-2；
    - round=1 紫队批判判缺口 valid=False，round>=2 补齐 valid=True；
    - 无 [round] 标记时完全回退旧静态响应（向后兼容）。

用无状态依赖的方式直接驱动 mock，断言确定性演化剧本。
"""

from __future__ import annotations

import json

from aegisos_agents.tools.llms.base import LLMRequest
from backend.mocks.cyber_provider import _CyberMockProvider


def _req(prompt: str) -> LLMRequest:
    return LLMRequest(prompt=prompt, model_id="mock")


def _json_text(resp):
    assert resp.ok and resp.text
    return json.loads(resp.text)


def test_base_recon_without_round_stays_static():
    """无 [round] 标记：recon 保持原始 2 资产，不触发演化。"""
    provider = _CyberMockProvider()
    data = _json_text(provider.complete(_req("Scan target range: 10.0.0.0/24")))
    assert len(data["assets"]) == 2
    assert {a["asset_id"] for a in data["assets"]} == {"asset-1", "asset-2"}


def test_recon_round2_exposes_new_asset():
    """round=2：侦察新暴露 asset-3。"""
    provider = _CyberMockProvider()
    data = _json_text(
        provider.complete(_req("Scan target range: 10.0.0.0/24 [round=2]"))
    )
    ids = {a["asset_id"] for a in data["assets"]}
    assert "asset-3" in ids
    assert len(data["assets"]) == 3


def test_exploit_round2_adds_step2():
    """round=2：利用链新增 step-2（打到 asset-3）。"""
    provider = _CyberMockProvider()
    data = _json_text(
        provider.complete(_req("Plan exploit chain for: [{}] [round=2]"))
    )
    step_ids = {s["step_id"] for s in data["steps"]}
    assert "step-1" in step_ids and "step-2" in step_ids


def test_critic_round1_gap_round2_ok():
    """紫队批判：round=1 判缺口(valid=False)，round=2 补齐(valid=True)。"""
    provider = _CyberMockProvider()
    r1 = _json_text(provider.complete(_req("Critique: {} [round=1]")))
    assert r1["valid"] is False
    assert len(r1["issues"]) >= 1

    r2 = _json_text(provider.complete(_req("Critique: {} [round=2]")))
    assert r2["valid"] is True
    assert r2["issues"] == []


def test_critic_without_round_stays_valid_true():
    """无 [round]：critic 保持旧静态 valid=True（既有测试兼容）。"""
    provider = _CyberMockProvider()
    data = _json_text(provider.complete(_req("Critique: {}")))
    assert data["valid"] is True
