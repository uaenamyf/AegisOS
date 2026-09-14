# date: 2026-09-14
# dev: OpenSquilla
# changelog: 新建 Chat 对话服务——普通对话走真实 LLM（端边云调度 + 记忆上下文），
# 替代此前"固定 handler 输出 JSON"的假对话链路。
"""Chat 对话服务 —— 通用对话的真实推理闭环。

背景（R23）：Chat 视图的普通消息此前被 ``TaskService._select_agent`` 兜底
路由到 ``recon`` 等攻防 Agent，输出固定预置 JSON，且前端硬编码"云侧推理"
徽标。本模块把"普通对话"从攻防演练链路中拆出来：

1. 意图分类（规则，零 token）：区分 演练 / 系统状态 / 通用对话；
2. 上下文组装：记忆召回（MemoryStore.recall）+ 会话近期消息，
   含隐私敏感文本时自动脱敏（敏感原文不出本地，与调度器隐私分级联动）；
3. 端边云真实推理：复用 ``ExecutionDispatcher``（含级联升级与降级重试），
   执行位置（tier/node/latency）以真实派发结果为准，不再由前端猜；
4. 无 Key / mock 模式 / 派发失败 → 明确标注降级来源，不再以假乱真。
"""

from __future__ import annotations

import re
from collections import deque
from typing import Any

from protocol.scheduler import Task

# 演练意图：与前端 chatIntent.ts 的 DRILL_PATTERN 语义对齐（后端兜底，
# 防止绕过前端直接 POST /tasks 时把演练请求当普通对话处理）
_DRILL_PATTERN = re.compile(
    r"(模拟.*攻防|红蓝紫|攻防演练|自动演练|完整.*演练|安全靶场|red.?blue.?purple)",
    re.IGNORECASE,
)
# 系统状态类问题：注入节点注册表与运行时模式的实时快照，让模型基于事实作答
_SYSTEM_STATUS_PATTERN = re.compile(
    r"(系统|平台|运行|当前|状态|健康|节点|架构|模式|节点数|在线)", re.IGNORECASE
)
_STATUS_QUERY_PATTERN = re.compile(
    r"(状态|健康|怎么样|情况|如何|在线|模式|架构|节点|summary|status|health)",
    re.IGNORECASE,
)
_MEMORY_TRIGGER_PATTERN = re.compile(
    r"(最近|上次|上一|之前|刚才|历史|回顾|recall|remember|earlier|last)",
    re.IGNORECASE,
)

_ASSISTANT_SYSTEM_PROMPT = (
    "你是 AegisOS 智能运维平台的对话助手。请用简洁、准确的自然语言（默认中文）"
    "回答用户问题；涉及系统或安全专业概念时可适当展开，但不要把答案写成 JSON "
    "或代码块，除非用户明确要求。"
)

# 会话近期消息缓冲：每会话保留最近 N 条（进程内，重启清空——演示场景可接受，
# 持久化历史由前端 store / MemoryStore 负责）
_MAX_TURNS = 6
_turns: dict[str, deque[dict[str, str]]] = {}


class ChatService:
    """通用对话服务。

    Attributes:
        infra_provider: 返回组合根 ``InfraService``（registry + dispatcher）的
            延迟回调，避免导入环；None 时按无基础设施处理（降级 mock 标注）。
        memory_provider: 返回共享 ``MemoryStore`` 单例的延迟回调。
        runtime_mode_provider: 返回 ``runtime_mode`` 模块的延迟回调（mock 判定）。
    """

    def __init__(
        self,
        infra_provider: Any = None,
        memory_provider: Any = None,
        runtime_mode_provider: Any = None,
    ) -> None:
        self._infra_provider = infra_provider
        self._memory_provider = memory_provider
        self._runtime_mode_provider = runtime_mode_provider

    # ---- 意图分类 ----

    @staticmethod
    def classify(goal: str) -> str:
        """规则意图分类：``drill`` | ``system_status`` | ``chat``。

        演练语义优先（安全边界：演练绝不能被当普通对话直接答掉）。
        """
        if _DRILL_PATTERN.search(goal or ""):
            return "drill"
        if _SYSTEM_STATUS_PATTERN.search(goal or "") and _STATUS_QUERY_PATTERN.search(
            goal or ""
        ):
            return "system_status"
        return "chat"

    # ---- 主入口 ----

    def chat(
        self,
        goal: str,
        session_id: str = "",
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """执行一轮通用对话，返回含真实执行位置的结果。

        Returns:
            ``{ok, text, tier, node_id, model_id, latency_ms, provider,
            privacy_note, routed, attempts, error}``。
            mock/离线降级时 ``tier="device"``、``provider="mock-local"``，
            并带中文 ``privacy_note`` 说明降级原因。
        """
        intent = self.classify(goal)
        context = self._build_context(goal, session_id, history, intent)
        prompt = self._compose_prompt(goal, context)
        dispatch = self._dispatch(prompt, system=_ASSISTANT_SYSTEM_PROMPT)
        dispatch["intent"] = intent
        self._remember(session_id, goal, dispatch)
        return dispatch

    # ---- 上下文组装 ----

    def _build_context(
        self,
        goal: str,
        session_id: str,
        history: list[dict[str, str]] | None,
        intent: str,
    ) -> dict[str, str]:
        parts: dict[str, str] = {}
        recent = self._recent_turns(session_id, history)
        if recent:
            parts["近期对话"] = recent
        memory = self._recall_memory(goal)
        if memory:
            parts["相关记忆"] = memory
        if intent == "system_status":
            snapshot = self._system_snapshot()
            if snapshot:
                parts["系统实时快照（JSON，已由平台采集，回答时请转述为自然语言）"] = snapshot
        return parts

    def _recent_turns(
        self, session_id: str, history: list[dict[str, str]] | None
    ) -> str:
        turns = _turns.get(session_id)
        lines: list[str] = []
        if turns:
            lines = [f"{t['role']}: {t['text'][:200]}" for t in turns][-_MAX_TURNS:]
        elif history:
            lines = [
                f"{m.get('role', 'user')}: {str(m.get('content', ''))[:200]}"
                for m in history
                if isinstance(m, dict) and m.get("content")
            ][-_MAX_TURNS:]
        return "\n".join(lines)

    def _recall_memory(self, goal: str) -> str:
        """从共享 MemoryStore 召回相关记忆摘要（失败静默，不阻断对话）。"""
        if self._memory_provider is None:
            return ""
        try:
            memory = self._memory_provider()
            if memory is None:
                return ""
            packets = memory.recall(goal) or []
            # 无字面命中时，"最近…"类追问取最近写入的摘要
            if not packets and _MEMORY_TRIGGER_PATTERN.search(goal or ""):
                packets = memory.recall("task") or []
            lines = [
                str(getattr(p, "summary", "") or "").strip()
                for p in packets[-3:]
                if getattr(p, "summary", "")
            ]
            return "\n".join(f"- {line}" for line in lines if line)
        except Exception:  # noqa: BLE001 —— 记忆不可用时按无记忆处理
            return ""

    def _system_snapshot(self) -> str:
        """采集端边云节点 + 运行时模式的实时快照，作为对话上下文。"""
        import json

        snapshot: dict[str, Any] = {}
        try:
            infra = self._infra_provider() if self._infra_provider else None
        except Exception:  # noqa: BLE001
            infra = None
        if infra is not None:
            try:
                snapshot["nodes"] = [
                    {
                        "node_id": s.get("node_id"),
                        "tier": s.get("tier"),
                        "status": s.get("status"),
                        "vendor": s.get("vendor"),
                    }
                    for s in infra.registry.snapshot()
                ]
                online = sum(1 for n in snapshot["nodes"] if n["status"] == "online")
                snapshot["online_count"] = f"{online}/{len(snapshot['nodes'])}"
            except Exception:  # noqa: BLE001
                pass
        try:
            runtime_mode = (
                self._runtime_mode_provider() if self._runtime_mode_provider else None
            )
            if runtime_mode is not None:
                desc = runtime_mode.describe()
                snapshot["runtime"] = {
                    "mode": desc.get("mode"),
                    "model": desc.get("model"),
                    "provider": desc.get("provider"),
                }
        except Exception:  # noqa: BLE001
            pass
        return json.dumps(snapshot, ensure_ascii=False) if snapshot else ""

    def _compose_prompt(self, goal: str, context: dict[str, str]) -> str:
        if not context:
            return goal
        # 上下文（记忆/历史/快照）先脱敏：注入的派生文本不应反向把整次请求
        # 判成 local（用户问题原文保持不脱敏，由派发器隐私分级处理）。
        from aegisos_agents.planning.engine.scheduler.privacy_classifier import (
            mask_sensitive,
        )

        try:
            context = {k: mask_sensitive(v) for k, v in context.items()}
        except Exception:  # noqa: BLE001 —— 脱敏不可用时按原文组装
            pass
        blocks = "\n".join(f"### {title}\n{body}" for title, body in context.items())
        return (
            "【平台上下文】\n"
            f"{blocks}\n\n"
            f"【用户问题】\n{goal}\n\n"
            "请结合上下文，用自然语言直接回答用户问题。"
        )

    # ---- 端边云真实推理 ----

    def _dispatch(self, prompt: str, *, system: str) -> dict[str, Any]:
        infra = None
        if self._infra_provider is not None:
            try:
                infra = self._infra_provider()
            except Exception:  # noqa: BLE001
                infra = None
        if infra is None:
            return self._degrade("基础设施未就绪，本回复为本地模拟输出（未调用大模型）")

        # 延迟预算 10s → 调度器按"算力优先"选云侧起步，失败自动降级边/端；
        # 隐私分级由 dispatcher 内部分类器实时决定（敏感文本强制本地）。
        task = Task(goal="chat", latency_budget=10.0, privacy="standard")
        try:
            result = infra.dispatcher.dispatch(
                task, prompt, required_capability="chat", system_prompt=system
            )
        except Exception as exc:  # noqa: BLE001 —— 派发异常不抛出，显式降级
            return self._degrade(f"节点派发异常（{exc}），本回复为本地模拟输出")

        attempts = list(getattr(result, "attempts", []) or [])
        if not result.ok or not (result.text or "").strip():
            reason = result.error or "all nodes returned empty"
            return self._degrade(f"端边云节点均不可用（{reason}），本回复为本地模拟输出")

        is_mock_node = "mock" in (result.model_id or "").lower()
        tier = str(result.tier or "cloud")
        # 真实执行位置：只有 OpenAI 兼容节点成功（非本地 mock 节点）才报厂商；
        # mock 节点输出绝不允许冒充云侧推理，provider 标为 mock-local。
        provider = ""
        if not is_mock_node:
            provider = self._detect_vendor(result.node_id)
        return {
            "ok": True,
            "text": str(result.text).strip(),
            "tier": tier,
            "node_id": result.node_id or "",
            "model_id": result.model_id or "",
            "latency_ms": getattr(result, "latency_ms", 0),
            "provider": provider,
            "privacy_note": str(getattr(result, "privacy_note", "") or ""),
            "routed": len(attempts) > 1,
            "attempts": attempts,
            "error": "",
        }

    def _detect_vendor(self, node_id: str) -> str:
        """从节点注册表取该节点的厂商（ark / deepseek / ollama ...）。"""
        try:
            infra = self._infra_provider() if self._infra_provider else None
            if infra is None:
                return ""
            for snap in infra.registry.snapshot():
                if snap.get("node_id") == node_id:
                    from infrastructure.nodes.descriptor import detect_vendor

                    return detect_vendor(str(snap.get("base_url", "")))
        except Exception:  # noqa: BLE001
            return ""
        return ""

    @staticmethod
    def _degrade(note: str) -> dict[str, Any]:
        """无 Key / mock 模式 / 节点不可用时的显式降级回复。

        不再返回固定 JSON：给一段诚实的本地兜底文本，并强制把 provider 标为
        ``mock-local``、tier 标为 ``device``（端侧），让前端徽标如实显示。
        """
        return {
            "ok": True,
            "text": (
                "当前未接入可用大模型，无法生成真实推理回答。\n"
                f"{note}。\n"
                "可在「运行配置」中配置 API Key 并切换到 real 模式后重试。"
            ),
            "tier": "device",
            "node_id": "local_fallback",
            "model_id": "mock-local",
            "latency_ms": 0,
            "provider": "mock-local",
            "privacy_note": note,
            "routed": False,
            "attempts": [],
            "error": "",
        }

    # ---- 会话内近期消息 ----

    def _remember(self, session_id: str, goal: str, dispatch: dict[str, Any]) -> None:
        if not session_id:
            return
        turns = _turns.setdefault(session_id, deque(maxlen=_MAX_TURNS * 2))
        turns.append({"role": "user", "text": goal})
        if dispatch.get("ok"):
            turns.append({"role": "assistant", "text": dispatch.get("text", "")})


__all__ = ["ChatService"]
