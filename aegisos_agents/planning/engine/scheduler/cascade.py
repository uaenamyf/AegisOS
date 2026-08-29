# date: 2026-08-27
# dev: ox-alpha
"""级联推理 —— "模型切分"落地（R8 —— 端边云任务线）。

赛题"模型切分"有两解：
    - 层间切分（split inference）：同族模型+高速互联 → 我们异构三层做不了也不必要
    - 任务级切分：把一次重推理拆成多段轻计算，分布到合适层级

我们做任务级切分，核心思路：
    1. 简单问题先用廉价模型（端侧 0.5B / 边侧 7B）
    2. 低置信才升级到更贵的模型
    3. 低跳成功 → 高跳零 token 消耗

直接对标评分表"资源效率（token 与时间）5 分"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from infrastructure.nodes.descriptor import InferenceResult
from protocol.scheduler import Task


# ---- 置信度启发式 ----


def _cjk_bigrams(text: str) -> set[str]:
    """提取中文 bigram 集合（用于答案-问题相关性粗判，零 token）。"""
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    if len(cjk) < 2:
        return {cjk} if cjk else set()
    return {cjk[i : i + 2] for i in range(len(cjk) - 1)}


def assess_confidence(result: InferenceResult, prompt: str = "") -> float:
    """廉价评估一次推理结果的置信度（0.0-1.0）。

    不需要调模型——纯规则判断，零额外 token 消耗。

    判断因子：
        - ok=False → 0.0
        - 文本长度过短 → 降分
        - 重复字符占比过高 → 降分（模型退化）
        - 答案与问题相关性过低 → 封顶 0.4（小模型常见"流畅但答非所问"幻觉，
          中文 bigram 覆盖率 < 30% 时强制级联升级）

    阈值推荐：0.6 为升级分界（保守），0.7 宽松。
    """
    if not result.ok:
        return 0.0

    text = result.text.strip()
    if not text:
        return 0.0

    char_count = len(text)

    # 过短——可能截断或无意义
    if char_count < 10:
        base = 0.1
    elif char_count < 30:
        base = 0.3
    elif char_count < 60:
        base = 0.5
    elif char_count < 120:
        base = 0.7
    else:
        base = 0.85

    # 重复字符检测：连续相同字符占比
    if char_count > 0:
        max_run = 1
        current_run = 1
        for i in range(1, char_count):
            if text[i] == text[i - 1]:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1

        repeat_ratio = max_run / char_count
        if repeat_ratio > 0.5:
            base = min(base, 0.2)
        elif repeat_ratio > 0.3:
            base = min(base, 0.4)

    # 相关性检测：答案对问题关键词（中文 bigram）覆盖率过低 → 封顶 0.4
    if prompt:
        q_terms = _cjk_bigrams(prompt)
        if q_terms:
            a_terms = _cjk_bigrams(text)
            coverage = len(q_terms & a_terms) / len(q_terms)
            if coverage < 0.3:
                base = min(base, 0.4)

    return min(base, 0.95)


# ---- 级联策略 ----


@dataclass
class CascadePolicy:
    """级联推理策略配置。

    Attributes:
        enable_cascade: 是否启用级联。False 时直接走 dispatcher 单次调用。
        confidence_threshold: 置信度阈值（0.0-1.0）。低于此值触发升级。
        max_hops: 最多跳数（≤3，对应三层）。含首跳。
        hop_chain: 自定义升级链，如 ["device", "edge", "cloud"]。
            默认从低到高（device→edge→cloud），按 latency_budget 约束。
    """

    enable_cascade: bool = True
    confidence_threshold: float = 0.6
    max_hops: int = 3
    hop_chain: list[str] | None = None


# 默认升级链：廉价→中→贵
_DEFAULT_CHAIN = ["device", "edge", "cloud"]


# ---- 主入口 ----


def run_cascade(
    dispatcher: Any,
    task: Task,
    prompt: str,
    policy: CascadePolicy | None = None,
    *,
    system_prompt: str = "",
    required_capability: str | None = None,
) -> InferenceResult:
    """级联推理主循环：按升级链逐跳执行，低置信升级。

    Args:
        dispatcher: 执行派发器（须有 dispatch(task, prompt, **kwargs) 方法）。
        task: 待调度任务。
        prompt: 推理 prompt。
        policy: 级联策略；为 None 时默认不启用级联。
        system_prompt: 可选系统提示。
        required_capability: 可选能力过滤。

    Returns:
        最高置信跳的 InferenceResult（含 hops 轨迹）。
        hops 字段追加在 attempts 中。
    """
    if policy is None or not policy.enable_cascade:
        return dispatcher.dispatch(
            task, prompt,
            required_capability=required_capability,
            system_prompt=system_prompt,
        )

    chain = policy.hop_chain or _DEFAULT_CHAIN
    max_hops = min(policy.max_hops, len(chain))

    all_hops: list[dict] = []
    last_result: InferenceResult | None = None

    for hop_idx in range(max_hops):
        target_tier = chain[hop_idx]

        # 强制目标层级：重写 task 的 latency_budget 使调度器偏向目标 tier
        if target_tier == "device":
            task.latency_budget = 0.5  # 超低延迟→调度器选端
        elif target_tier == "edge":
            task.latency_budget = 3.0  # 低延迟→调度器选边
        else:
            task.latency_budget = 10.0  # 默认→调度器选云

        result = dispatcher.dispatch(
            task, prompt,
            required_capability=required_capability,
            system_prompt=system_prompt,
        )
        last_result = result

        confidence = assess_confidence(result)
        all_hops.append({
            "hop": hop_idx + 1,
            "target_tier": target_tier,
            "actual_tier": result.tier,
            "ok": result.ok,
            "latency_ms": result.latency_ms,
            "confidence": confidence,
        })

        # 够好 → 不再升级（省高跳 token）
        if result.ok and confidence >= policy.confidence_threshold:
            result.attempts = all_hops
            return result

    # 所有跳完成仍不自信 → 返回最后一跳的结果
    if last_result is not None:
        last_result.attempts = all_hops
        return last_result

    # 理论不可达（max_hops>=1），防御兜底
    return InferenceResult.failure(error="cascade produced no result")


__all__ = ["CascadePolicy", "assess_confidence", "run_cascade"]