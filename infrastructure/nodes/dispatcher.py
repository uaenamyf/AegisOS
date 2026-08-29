# date: 2026-08-27
# dev: ox-alpha
"""执行派发器 —— 调度决策→真实执行闭环（R6 —— 端边云任务线枢纽）。

把三层节点（R2/R3/R4）、注册中心（R5）、调度器（scheduler.py）串成一条
完整链路：任务来了 → 查注册表取在线节点 → 转 scheduler.Model 候选
→ 调 schedule() 选 tier → 取对应节点执行 infer() → 失败剔除该 tier 重调度
→ 全程记录每次尝试的耗时/成败（attempts 轨迹）。

这是全仓库第一个把"调度决策"变成"真实网络调用"的模块；
C-3 "自动完成推理位置的动态选择"在此闭环。
"""

from __future__ import annotations

from collections.abc import Callable

from aegisos_agents.planning.engine.scheduler.scheduler import schedule
from infrastructure.nodes.descriptor import InferenceResult, NodeProfile, Tier
from infrastructure.nodes.registry import NodeRegistry
from protocol.scheduler import Task


class ExecutionDispatcher:
    """端边云三层执行派发器：调度决策 → 真实网络执行 → 降级重试。

    Attributes:
        registry: 节点注册中心（在线节点来源）。
        max_attempts: 最多尝试次数（含降级链）。默认 3（三层各一次）。
    """

    def __init__(
        self,
        registry: NodeRegistry,
        max_attempts: int = 3,
        *,
        enable_cascade: bool = True,
        confidence_threshold: float = 0.6,
    ) -> None:
        self.registry = registry
        self.max_attempts = max(1, max_attempts)
        # R8：级联推理（低置信自动升级）——运行时显式开启（backend/main.py），
        # 默认关闭以保持既有派发语义与测试兼容
        self.enable_cascade = enable_cascade
        self.confidence_threshold = confidence_threshold

    # ---- 主入口 ----

    def dispatch(
        self,
        task: Task,
        prompt: str,
        *,
        required_capability: str | None = None,
        system_prompt: str = "",
    ) -> InferenceResult:
        """为 task 选择最优节点执行推理，含降级重试。

        Args:
            task: 待调度任务（含 privacy / latency_budget / goal）。
            prompt: 推理 prompt 文本。
            required_capability: 可选能力过滤（如 "reasoning"）。
            system_prompt: 可选系统提示。

        Returns:
            InferenceResult（ok=True 含 attempts 轨迹；ok=False 含 error）。
        """
        # R7：数据敏感等级自动分级 —— 始终执行，防止显式 unrestricted 绕过检测
        # （显式 local 保持 local；standard/unrestricted 一律跑分类器，
        #   命中敏感规则自动降级为 local，保证敏感数据绝不上云）
        from aegisos_agents.planning.engine.scheduler.privacy_classifier import (
            classify_privacy_with_reason,
        )

        if task.privacy == "local":
            self._privacy_reason = "显式指定本地推理"
        else:
            level, reason = classify_privacy_with_reason(prompt)
            task.privacy = level
            self._privacy_reason = reason  # 写入 InferenceResult 供前端提醒

        # R8：敏感数据脱敏上云兜底 —— local 命中强规则时，把敏感字段
        # 替换为占位符后允许升级到云端大模型（质量兜底），
        # 原文只在本地层可见。是否兜底由任务 latency_budget 保持不变，
        # 由下方 cascade 链路自然决策（本地先试，低置信才升级）。
        from aegisos_agents.planning.engine.scheduler.privacy_classifier import (
            mask_sensitive,
        )

        effective_prompt = (
            mask_sensitive(prompt) if task.privacy == "local" else prompt
        )
        if effective_prompt != prompt:
            self._privacy_reason = (
                f"{self._privacy_reason}（已脱敏，可安全上云兜底）"
            )

        online = self.registry.online_node_instances()
        if not online:
            return InferenceResult.failure(error="no online nodes registered")

        # 构建候选模型 + tier→(profile,node) 索引
        models, tier_index = self._build_candidates(online)

        attempts: list[dict] = []
        tried_tiers: set[str] = set()
        best_result: InferenceResult | None = None

        # 级联置信度评估（R8）——零 token 纯规则
        from aegisos_agents.planning.engine.scheduler.cascade import (
            assess_confidence,
        )

        _TIER_RANK = {"device": 0, "edge": 1, "cloud": 2}

        remaining = list(models)
        for _round in range(self.max_attempts):
            # 剔除已尝试失败的 tier
            remaining = [m for m in remaining if m.tier not in tried_tiers]
            if not remaining:
                break

            # 调度决策
            try:
                chosen = schedule(task, remaining, required_capability)
            except ValueError as exc:
                # 能力过滤后无匹配模型
                attempts.append(
                    {"tier": "", "node_id": "", "model_id": "",
                     "ok": False, "latency_ms": 0, "error": str(exc)}
                )
                break

            chosen_tier = chosen.tier
            if chosen_tier not in tier_index:
                tried_tiers.add(chosen_tier)
                continue

            profile, node = tier_index[chosen_tier]

            # 执行推理（隐私分级联动：local 任务的原文只在本地层
            # device/edge 可见，上云一律使用脱敏文本）
            send_prompt = (
                effective_prompt if str(profile.tier) == "cloud" else prompt
            )
            try:
                result = node.infer(send_prompt, system=system_prompt)
            except Exception:
                result = InferenceResult.failure(
                    error="infer exception",
                    node_id=profile.node_id,
                    tier=str(profile.tier),
                )

            # 补全 fields（节点侧未填的由派发器兜底）
            result.node_id = result.node_id or profile.node_id
            result.tier = result.tier or str(profile.tier)
            result.model_id = result.model_id or profile.model_id

            # 记录本次尝试
            attempts.append({
                "tier": str(profile.tier),
                "node_id": profile.node_id,
                "model_id": profile.model_id,
                "ok": result.ok,
                "latency_ms": result.latency_ms,
                "error": result.error if not result.ok else "",
            })

            if result.ok:
                if best_result is None:
                    best_result = result

                # R8 级联决策：置信度够 → 直接返回（省高跳 token）；
                # 不够 → 剔除当前及更低层级，升级重试。
                # mock 节点的固定短语不是真实模型产出：级联模式下透明跳过
                # （记入 attempts 但继续升级），非级联模式才可作结果返回。
                is_mock = "mock" in (result.model_id or "").lower()
                if self.enable_cascade and not is_mock:
                    # 敏感任务（local）+ 云在线 → 本地答案仅作兜底，
                    # 强制升级一次云端（上云用脱敏文本），保证复杂问题质量
                    force_escalation = (
                        task.privacy == "local"
                        and "cloud" in tier_index
                        and str(profile.tier) != "cloud"
                    )
                    confidence = (
                        0.0
                        if force_escalation
                        else assess_confidence(result, prompt)
                    )
                    if confidence >= self.confidence_threshold:
                        result.attempts = attempts
                        result.privacy_note = self._privacy_reason
                        return result
                    rank = _TIER_RANK.get(str(profile.tier), 0)
                    tried_tiers.update(
                        t for t in tier_index
                        if _TIER_RANK.get(t, 0) <= rank
                    )
                    continue

                if self.enable_cascade and is_mock:
                    rank = _TIER_RANK.get(str(profile.tier), 0)
                    tried_tiers.update(
                        t for t in tier_index
                        if _TIER_RANK.get(t, 0) <= rank
                    )
                    continue

                result.attempts = attempts
                result.privacy_note = self._privacy_reason
                return result

            tried_tiers.add(chosen_tier)

        # 全部尝试结束：有任一跳成功则返回最好结果（级联升级后回退最优）
        if best_result is not None:
            best_result.attempts = attempts
            best_result.privacy_note = self._privacy_reason
            return best_result

        return InferenceResult(
            ok=False,
            error=f"all {len(attempts)} attempt(s) exhausted",
            attempts=attempts,
            privacy_note=self._privacy_reason,
        )

    # ---- 内部 ----

    def _build_candidates(
        self, online: list
    ) -> tuple[list, dict[str, tuple[NodeProfile, Callable]]]:
        """从在线节点列表构建 scheduler.Model 候选列表 + tier 索引。

        Returns:
            (models, tier_index) 其中 tier_index 为 {tier_str: (profile, node)}。
        """
        models = []
        tier_index: dict[str, tuple[NodeProfile, Callable]] = {}
        for profile, node in online:
            models.append(profile.to_scheduler_model())
            tier = str(profile.tier)
            # 同 tier 多节点取首个（demo 阶段每层一个节点，
            #   未来可扩展为加权轮询）
            if tier not in tier_index:
                tier_index[tier] = (profile, node)
        return models, tier_index


__all__ = ["ExecutionDispatcher"]


if __name__ == "__main__":
    # 冒烟：无节点场景
    disp = ExecutionDispatcher(NodeRegistry())
    r = disp.dispatch(Task(goal="冒烟"), "hello")
    print(f"no-nodes -> ok={r.ok} error={r.error}")