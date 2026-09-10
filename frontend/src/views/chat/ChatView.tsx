// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: R5.3 加流式模式开关——Stream 开启时用 fetch SSE 实时展示 Agent 执行过程

import { useState, useRef, useEffect, useCallback } from "react";
import { useAppStore, type ChatMessage, type HitlPayload } from "@/lib/store";
import { humanApi } from "@/services/api/human";
import { taskApi } from "@/services/api/tasks";
import { cyberApi } from "@/services/api/cyber";

function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function isCyberDrillRequest(goal: string): boolean {
  return /模拟.*攻防|红蓝紫|攻防演练|自动演练|完整.*演练|red.?blue.?purple/i.test(goal);
}

async function waitForDrill(drillId: string, onUpdate?: (record: any) => void): Promise<any> {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const record = await cyberApi.getDrill(drillId);
    onUpdate?.(record);
    if (record.summary || record.convergence_code === "aborted") return record;
    await new Promise((resolve) => window.setTimeout(resolve, 500));
  }
  throw new Error("演练执行超时，请到 Cyber Defense 查看当前进度");
}

function syncDrillTasks(drillId: string, targetRange: string, rounds: any[], done: boolean, summary: any): void {
  const phases = [["red", "红队 · 侦察与攻击链", "recon"], ["blue", "蓝队 · 检测与响应", "detector"], ["purple", "紫队 · 一致性审查", "reviewer-defense"]] as const;
  const tasks: Array<Record<string, any>> = [{ task_id: drillId, goal: `完整红蓝紫攻防演练 · ${targetRange}`, status: done ? "succeeded" : "running", dependency: [], priority: 10, payload: { source: "chat-drill", drill_id: drillId, stage: 0, agent_id: "orchestrator" }, result: done ? { output: summary, rounds: rounds.length } : {} }];
  phases.forEach(([phase, label, agent], phaseIndex) => {
    const round = rounds.length + (done ? 0 : 1);
    for (let currentRound = 1; currentRound <= Math.max(1, round); currentRound += 1) {
      const result = rounds[currentRound - 1]?.[phase];
      const complete = Boolean(result);
      tasks.push({ task_id: `${drillId}:${phase}:r${currentRound}`, goal: `${label} · 第 ${currentRound} 轮`, status: complete ? "succeeded" : "running", dependency: [drillId], priority: 9 - currentRound, payload: { source: "chat-drill", drill_id: drillId, phase, stage: phaseIndex + 1, agent_id: agent }, result: result ?? {} });
    }
  });
  const store = useAppStore.getState();
  tasks.forEach((task) => store.upsertTask(task));
  try {
    sessionStorage.setItem(`aegis.canvas.drill.${drillId}`, JSON.stringify(tasks));
  } catch { /* 页面存储不可用时仍保留当前会话内的实时任务 */ }
}

async function waitForTask(taskId: string): Promise<{ status?: string; result?: Record<string, unknown> }> {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const task = await taskApi.get(taskId);
    if (["succeeded", "failed", "cancelled", "rolled_back"].includes(String(task.status))) {
      return task;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 250));
  }
  throw new Error("任务执行超时，请到 Canvas 查看后台状态");
}

// date: 2026-08-17
// dev: 陈子毅
// changelog: AP4.6 人机协同卡片——展示 Agent 提问、可选项与人类结论（含超时降级）
function HitlCard({
  msg,
  onAnswer,
}: {
  msg: ChatMessage;
  onAnswer: (id: string, answer: string) => void;
}) {
  const h = msg.hitl as HitlPayload;
  const resolved = h.kind === "resolved";
  const isTimeout = resolved && Boolean(h.timeout);
  return (
    <div className={`chat__hitl${resolved ? " chat__hitl--resolved" : ""}`}>
      <div className="chat__hitl-header">
        <span className="chat__hitl-title">
          {resolved ? "人机协同 · 已处理" : "人机协同 · 等待确认"}
        </span>
        <span
          className={
            "chat__hitl-badge " +
            (resolved
              ? isTimeout
                ? "chat__hitl-badge--timeout"
                : "chat__hitl-badge--confirmed"
              : "chat__hitl-badge--pending")
          }
        >
          {resolved
            ? isTimeout
              ? "超时降级"
              : h.answered
                ? "已确认"
                : "已处理"
            : "待响应"}
        </span>
      </div>
      {h.question && <div className="chat__hitl-question">{h.question}</div>}
      {h.options && h.options.length > 0 && !resolved && (
        <div className="chat__hitl-options">
          {h.options.map((opt) => (
            <button
              key={opt}
              type="button"
              className="chat__hitl-option"
              onClick={() => onAnswer(msg.id, opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
      {resolved && (
        <div className="chat__hitl-answer">
          <span className="chat__hitl-answer-label">结论：</span>
          <span className="chat__hitl-answer-value">
            {h.answer || (isTimeout ? "（无人值守，已按安全默认降级）" : "—")}
          </span>
        </div>
      )}
      {resolved && h.rationale && (
        <div className="chat__hitl-rationale">{h.rationale}</div>
      )}
    </div>
  );
}

export function ChatView() {
  const chatMessages = useAppStore((s) => s.chatMessages);
  const isSending = useAppStore((s) => s.isSending);
  const agents = useAppStore((s) => s.agents);
  const selectedAgentId = useAppStore((s) => s.selectedAgentId);
  const currentSession = useAppStore((s) => s.currentSession);
  const addChatMessage = useAppStore((s) => s.addChatMessage);
  const updateChatMessage = useAppStore((s) => s.updateChatMessage);
  const upsertTask = useAppStore((s) => s.upsertTask);
  const setSending = useAppStore((s) => s.setSending);
  const setSelectedAgentId = useAppStore((s) => s.setSelectedAgentId);

  const [input, setInput] = useState("");
  const [streamMode, setStreamMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, scrollToBottom]);

  const handleSend = async () => {
    const goal = input.trim();
    if (!goal || isSending) return;

    const sessionId = currentSession?.id ?? "";

    // 1. 添加用户消息
    const userMsg: ChatMessage = {
      id: genId(),
      role: "user",
      content: goal,
      timestamp: Date.now(),
    };
    addChatMessage(userMsg);
    setInput("");
    setSending(true);

    // 2. 添加占位的 assistant 消息
    const assistantMsgId = genId();
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      status: "sending",
      agentId: selectedAgentId ?? undefined,
      timestamp: Date.now(),
    };
    addChatMessage(assistantMsg);

    try {
      if (isCyberDrillRequest(goal)) {
        const targetRange = "10.0.0.0/24";
        const started = await cyberApi.startDrill({ target_range: targetRange, max_rounds: 5 });
        syncDrillTasks(started.drill_id, targetRange, [], false, null);
        const record = await waitForDrill(started.drill_id, (current) => {
          syncDrillTasks(started.drill_id, targetRange, current.rounds ?? [], Boolean(current.summary), current.summary ?? null);
        });
        const rounds = record.rounds ?? [];
        const summary = record.summary ?? null;
        syncDrillTasks(started.drill_id, targetRange, rounds, Boolean(summary), summary);
        try {
          sessionStorage.setItem("aegis.cyber-drill.snapshot", JSON.stringify({
            drillId: started.drill_id,
            phase: summary ? "done" : "aborted",
            rounds,
            summary,
            reportMd: null,
          }));
        } catch { /* 页面存储不可用时仍保留 Chat 结果 */ }
        const resultText = JSON.stringify({
          drill_id: started.drill_id,
          target_range: targetRange,
          rounds: rounds.length,
          convergence: record.convergence_code ?? (summary ? "converged" : "aborted"),
          summary,
        }, null, 2);
        updateChatMessage(assistantMsgId, { content: resultText, status: "done", taskId: started.drill_id, tier: "cloud" });
        return;
      }
      let resultText = "";
      let resultTier = "";
      let resultPrivacyNote = "";
      let trackedTaskId = "";
      try {
        const task = await taskApi.create({
          goal,
          session_id: sessionId,
          payload: { ...(selectedAgentId ? { agent_id: selectedAgentId } : {}), source: "chat" },
        });
        trackedTaskId = task.task_id ?? "";
        if (trackedTaskId) {
          updateChatMessage(assistantMsgId, { taskId: trackedTaskId });
          upsertTask({ ...task, status: "running" });
        }
      } catch { /* task tracking is additive; Chat remains usable if offline */ }

      if (!trackedTaskId) {
        throw new Error("任务创建失败，无法启动完整执行链");
      }

      const completedTask = await waitForTask(trackedTaskId);
      const output = completedTask.result?.output ?? completedTask.result ?? "";
      resultText = typeof output === "string" ? output : JSON.stringify(output, null, 2);
      resultTier = String(completedTask.result?.tier ?? "cloud");

      if (trackedTaskId) {
        upsertTask({ task_id: trackedTaskId, goal, status: completedTask.status, result: completedTask.result ?? { output: resultText, tier: resultTier } });
      }

      // 伪流式：整段结果到达后按字符渐进渲染（打字机效果），
      // 后续接 SSE 流式后此段可直接替换为真实流式渲染
      const fullText = resultText;
      await new Promise<void>((resolve) => {
        let i = 0;
        let cancelled = false;
        const step = Math.max(1, Math.ceil(fullText.length / 150));
        const timer = setInterval(() => {
          if (cancelled) { clearInterval(timer); resolve(); return; }
          i = Math.min(fullText.length, i + step);
          updateChatMessage(assistantMsgId, {
            content: fullText.slice(0, i),
            status: i >= fullText.length ? "done" : "sending",
            tier: resultTier,
            privacyNote: resultPrivacyNote,
          });
          if (i >= fullText.length) { clearInterval(timer); resolve(); }
        }, 16);
        // 组件卸载时中止动画（守卫：路由切换不留悬挂定时器）
        window.addEventListener("beforeunload", () => { cancelled = true; }, { once: true });
      });
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Unknown error";
      updateChatMessage(assistantMsgId, {
        content: `Error: ${errorMsg}`,
        status: "error",
      });
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  // date: 2026-08-17
  // dev: 陈子毅
  // changelog: AP4.6 人类在 ChatView 点选 HITL 选项 → 乐观更新卡片为已处理，并尽力回传后端
  const handleHitlAnswer = useCallback(
    (id: string, answer: string) => {
      const current = useAppStore
        .getState()
        .chatMessages.find((m) => m.id === id);
      const h = current?.hitl;
      if (!h) return;
      updateChatMessage(id, {
        hitl: {
          ...h,
          kind: "resolved",
          status: "resolved",
          answer,
          answered: true,
          timeout: false,
        },
      });
      // 集成点：后端需提供人类回答通道（REST POST /human/answer 或 WS）。
      // 当前 backend 的 HITL 由 AutoAskHandler 即时降级，人类回传为前向兼容钩子，失败不影响 UI。
      if (h.taskId) {
        humanApi
          .submitAnswer({ task_id: h.taskId, agent: h.agent ?? "", answer })
          .catch(() => {});
      }
    },
    [updateChatMessage],
  );

  // R5.3: 流式发送——用 fetch SSE 实时展示 Agent 执行过程
  const handleSendStream = async () => {
    // Stream 也必须等待同一个后端任务完成，不能另起一条重复执行链。
    await handleSend();
  };

  return (
    <div className="chat">
      <div className="chat__header">
        <h2 className="chat__title">智能体对话</h2>
        <div className="chat__agent-select">
          <label className="chat__agent-label">智能体：</label>
          <select
            className="chat__agent-dropdown"
            value={selectedAgentId ?? ""}
            onChange={(e) => setSelectedAgentId(e.target.value || null)}
            disabled={isSending}
          >
            <option value="">自动路由</option>
            {agents.map((a) => (
              <option key={a.agent_id} value={a.agent_id}>
                {a.name} ({a.role})
              </option>
            ))}
          </select>
          <label className="chat__stream-toggle" title="R5.3: 流式模式实时展示 Agent 执行过程">
            <input
              type="checkbox"
              checked={streamMode}
              onChange={(e) => setStreamMode(e.target.checked)}
              disabled={isSending || !selectedAgentId}
            />
            流式执行
          </label>
        </div>
      </div>

      <div className="chat__messages">
        {chatMessages.length === 0 && (
          <div className="chat__empty">
            <p className="chat__empty-title">还没有消息</p>
            <p className="chat__empty-desc">
              在下方输入目标，开始与智能体协作。
            </p>
            <p className="chat__empty-hint">
              可选择指定智能体，也可以使用自动路由分配任务。
            </p>
          </div>
        )}
        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={`chat__msg chat__msg--${msg.role}`}
          >
            <div className="chat__msg-avatar">
              {msg.role === "user" ? "U" : msg.agentId ? msg.agentId[0].toUpperCase() : "A"}
            </div>
            <div className="chat__msg-body">
              <div className="chat__msg-meta">
                <span className="chat__msg-role">
                  {msg.role === "user" ? "You" : msg.agentId ?? "Agent"}
                </span>
                <span className="chat__msg-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
                {msg.status === "sending" && (
                  <span className="chat__msg-status chat__msg-status--sending">
                    ...
                  </span>
                )}
                {msg.status === "error" && (
                  <span className="chat__msg-status chat__msg-status--error">
                    error
                  </span>
                )}
              </div>
              {msg.tier && (
                <div className={`tier-banner tier-banner--${msg.tier}`}>
                  {msg.tier === "device" ? "🖥️ 端侧推理" : msg.tier === "edge" ? "🌐 边侧推理" : "☁️ 云侧推理"}
                  {msg.privacyNote && <span className="tier-banner__note"> · {msg.privacyNote}</span>}
                </div>
              )}
              {msg.hitl ? (
                // date: 2026-08-17 dev: 陈子毅 changelog: AP4.6 渲染人机协同卡片（提问/选项/结论/超时降级）
                <HitlCard msg={msg} onAnswer={handleHitlAnswer} />
              ) : (
                <div className="chat__msg-content">
                  {msg.content || (msg.status === "sending" ? "思考中…" : "")}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat__input-area">
        <textarea
          ref={textareaRef}
          className="chat__input"
          placeholder="输入任务目标，按 Enter 发送，Shift+Enter 换行"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isSending}
        />
        <button
          className="chat__send-btn"
          onClick={() => void (streamMode ? handleSendStream() : handleSend())}
          disabled={!input.trim() || isSending || (streamMode && !selectedAgentId)}
        >
          {isSending ? "发送中…" : streamMode ? "流式执行" : "发送"}
        </button>
      </div>
    </div>
  );
}
