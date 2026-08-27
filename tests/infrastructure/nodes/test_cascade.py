"""R8 级联推理 —— 单元测试。

覆盖：
    ① 首跳高置信不升级（省 token）
    ② 低置信逐级升级
    ③ max_hops 截断
    ④ 级联关闭时直接走 dispatcher
    ⑤ 置信度启发式各因子
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from aegisos_agents.planning.engine.scheduler.cascade import (
    CascadePolicy,
    assess_confidence,
    run_cascade,
)
from infrastructure.nodes.descriptor import InferenceResult
from protocol.scheduler import Task


# ---- Fake Dispatcher ----


@dataclass
class FakeDispatcher:
    """按预设序列返回结果的假派发器。"""

    results: list[InferenceResult] = field(default_factory=list)
    call_count: int = 0
    prompts_seen: list[str] = field(default_factory=list)

    def dispatch(
        self,
        task: Task,
        prompt: str,
        *,
        required_capability: str | None = None,
        system_prompt: str = "",
    ) -> InferenceResult:
        self.prompts_seen.append(prompt)
        if self.call_count < len(self.results):
            r = self.results[self.call_count]
            self.call_count += 1
            return r
        # 兜底：返回成功空结果
        self.call_count += 1
        return InferenceResult(ok=True, text="fallback", tier="cloud")


def _task(latency: float = 10.0) -> Task:
    return Task(goal="test", latency_budget=latency)


# ---------- 置信度启发式 ----------


def test_confidence_long_answer_is_high():
    r = InferenceResult(ok=True, text="这是一段足够长的回答，包含了完整的分析内容。" * 3)
    assert assess_confidence(r) >= 0.7


def test_confidence_short_answer_is_low():
    r = InferenceResult(ok=True, text="ok")
    assert assess_confidence(r) < 0.5


def test_confidence_failed_result_is_zero():
    r = InferenceResult(ok=False, error="timeout")
    assert assess_confidence(r) == 0.0


def test_confidence_empty_text_is_low():
    r = InferenceResult(ok=True, text="")
    assert assess_confidence(r) < 0.3


def test_confidence_repeated_chars_is_low():
    """输出全是重复字符（模型退化）→ 低置信。"""
    r = InferenceResult(ok=True, text="啊啊啊啊啊啊啊啊啊啊啊啊")
    assert assess_confidence(r) < 0.5


# ---------- 级联主循环 ----------


def test_first_hop_high_confidence_no_escalation():
    """首跳（端侧）返回高质量回答 → 不升级，省了云 token。"""
    device_result = InferenceResult(
        ok=True,
        text="这是一段完整的分析回答，内容详实逻辑清晰，对攻击链进行了全面梳理，覆盖了检测、溯源与修复的完整过程。" * 2,
        tier="device",
        usage={"prompt_tokens": 10, "completion_tokens": 30},
    )
    disp = FakeDispatcher(results=[device_result])
    policy = CascadePolicy(enable_cascade=True, confidence_threshold=0.6, max_hops=3)

    result = run_cascade(disp, _task(), "分析这段日志", policy)

    assert result.ok is True
    assert result.tier == "device"
    assert disp.call_count == 1  # 只调了一次，没升级


def test_low_confidence_escalates_to_next_hop():
    """首跳低置信 → 升级到下一跳。"""
    device_result = InferenceResult(
        ok=True, text="嗯", tier="device",
        usage={"prompt_tokens": 5, "completion_tokens": 1},
    )
    edge_result = InferenceResult(
        ok=True, text="这是边侧模型的完整分析回答，内容详尽覆盖了所有要点并给出了明确的处置建议。" * 2,
        tier="edge",
        usage={"prompt_tokens": 10, "completion_tokens": 25},
    )
    disp = FakeDispatcher(results=[device_result, edge_result])
    policy = CascadePolicy(enable_cascade=True, confidence_threshold=0.6, max_hops=3)

    result = run_cascade(disp, _task(), "复杂分析任务", policy)

    assert result.ok is True
    assert result.tier == "edge"  # 升级到边侧
    assert disp.call_count == 2


def test_max_hops_truncation():
    """所有跳都低置信 → max_hops 截断，返回最后一次结果。"""
    low1 = InferenceResult(ok=True, text="?", tier="device")
    low2 = InferenceResult(ok=True, text="??", tier="edge")
    low3 = InferenceResult(ok=True, text="???", tier="cloud")
    disp = FakeDispatcher(results=[low1, low2, low3])
    policy = CascadePolicy(enable_cascade=True, confidence_threshold=0.9, max_hops=3)

    result = run_cascade(disp, _task(), "超难问题", policy)

    assert disp.call_count == 3  # 三跳全跑了
    assert result.tier == "cloud"  # 返回最后一跳


def test_cascade_disabled_uses_dispatcher_directly():
    """级联关闭 → 直接调一次 dispatcher。"""
    cloud_result = InferenceResult(
        ok=True, text="云端回答", tier="cloud",
        usage={"prompt_tokens": 20, "completion_tokens": 40},
    )
    disp = FakeDispatcher(results=[cloud_result])
    policy = CascadePolicy(enable_cascade=False)

    result = run_cascade(disp, _task(), "普通问题", policy)

    assert result.ok is True
    assert disp.call_count == 1


def test_cascade_records_all_hops_in_attempts():
    """级联轨迹记录在 attempts 字段。"""
    r1 = InferenceResult(ok=True, text="短", tier="device", latency_ms=50)
    r2 = InferenceResult(
        ok=True, text="完整的云端分析回答，内容详尽覆盖所有要点并给出纵深防御方案。" * 2,
        tier="cloud", latency_ms=500,
    )
    disp = FakeDispatcher(results=[r1, r2])
    policy = CascadePolicy(enable_cascade=True, confidence_threshold=0.6, max_hops=3)

    result = run_cascade(disp, _task(), "测试轨迹", policy)

    assert len(result.attempts) >= 2
    assert result.attempts[0]["actual_tier"] == "device"
    assert result.attempts[1]["actual_tier"] == "cloud"


def test_cascade_token_saving_evident():
    """级联开启时，低跳成功 → 高跳 token=0（省 token 证据）。"""
    device_result = InferenceResult(
        ok=True, text="这是一段足够长的完整回答，覆盖了问题所有方面并给出了清晰结论。" * 2, tier="device",
        usage={"prompt_tokens": 10, "completion_tokens": 30},
    )
    disp = FakeDispatcher(results=[device_result])
    policy = CascadePolicy(enable_cascade=True, confidence_threshold=0.6, max_hops=3)

    result = run_cascade(disp, _task(), "简单问题", policy)

    # 只调了端侧，没调云 → 云 token = 0
    assert disp.call_count == 1
    assert result.tier == "device"
    # attempts 里只有一条记录
    assert len(result.attempts) == 1
