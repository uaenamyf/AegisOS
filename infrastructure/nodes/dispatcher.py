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

    def __init__(self, registry: NodeRegistry, max_attempts: int = 3) -> None:
        self.registry = registry
        self.max_attempts = max(1, max_attempts)

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
        online = self.registry.online_node_instances()
        if not online:
            return InferenceResult.failure(error="no online nodes registered")

        # 构建候选模型 + tier→(profile,node) 索引
        models, tier_index = self._build_candidates(online)

        attempts: list[dict] = []
        tried_tiers: set[str] = set()

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

            # 执行推理
            try:
                result = node.infer(prompt, system=system_prompt)
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
                result.attempts = attempts
                return result

            tried_tiers.add(chosen_tier)

        # 全部尝试失败
        return InferenceResult(
            ok=False,
            error=f"all {len(attempts)} attempt(s) exhausted",
            attempts=attempts,
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