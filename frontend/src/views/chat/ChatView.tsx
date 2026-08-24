// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: R5.3 加流式模式开关——Stream 开启时用 fetch SSE 实时展示 Agent 执行过程

import { useState, useRef, useEffect, useCallback } from "react";
import { useAppStore, type ChatMessage, type HitlPayload } from "@/lib/store";
import { agentApi } from "@/services/api/agents";
import { taskApi } from "@/services/api/tasks";
import { streamAgent } from "@/services/api/stream";
import { humanApi } from "@/services/api/human";

function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
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
      let resultText = "";

      if (selectedAgentId) {
        // 直调指定 Agent
        const res = await agentApi.invokeAgent(selectedAgentId, {
          goal,
          session_id: sessionId,
        });
        const output = res.result?.output;
        resultText =
          typeof output === "string"
            ? output
            : JSON.stringify(output ?? res.result, null, 2);
      } else {
        // 提交任务（由 agents 域内部路由决定用哪个 Agent）
        const task = await taskApi.create({ goal, session_id: sessionId });
        resultText = `Task created: ${task.task_id}\nStatus: ${task.status}\nPlan: ${JSON.stringify(task.plan)}`;
      }

      updateChatMessage(assistantMsgId, {
        content: resultText,
        status: "done",
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
    const goal = input.trim();
    if (!goal || isSending || !selectedAgentId) return;

    const userMsg: ChatMessage = {
      id: genId(),
      role: "user",
      content: goal,
      timestamp: Date.now(),
    };
    addChatMessage(userMsg);
    setInput("");
    setSending(true);

    const assistantMsgId = genId();
    addChatMessage({
      id: assistantMsgId,
      role: "assistant",
      content: "",
      status: "sending",
      agentId: selectedAgentId,
      timestamp: Date.now(),
    });

    let accumulated = "";
    await streamAgent(selectedAgentId, goal, (evt) => {
      if (evt.event === "error") {
        updateChatMessage(assistantMsgId, {
          content: `Stream error: ${JSON.stringify(evt.data)}`,
          status: "error",
        });
      } else {
        accumulated += `[${evt.event}] ${JSON.stringify(evt.data, null, 2)}\n`;
        updateChatMessage(assistantMsgId, {
          content: accumulated,
          status: "sending",
        });
      }
    });

    updateChatMessage(assistantMsgId, { status: "done" });
    setSending(false);
  };

  return (
    <div className="chat">
      <div className="chat__header">
        <h2 className="chat__title">Agent Chat</h2>
        <div className="chat__agent-select">
          <label className="chat__agent-label">Agent:</label>
          <select
            className="chat__agent-dropdown"
            value={selectedAgentId ?? ""}
            onChange={(e) => setSelectedAgentId(e.target.value || null)}
            disabled={isSending}
          >
            <option value="">Auto (route)</option>
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
            Stream
          </label>
        </div>
      </div>

      <div className="chat__messages">
        {chatMessages.length === 0 && (
          <div className="chat__empty">
            <p className="chat__empty-title">No messages yet</p>
            <p className="chat__empty-desc">
              Send a message below to start a conversation with an agent.
            </p>
            <p className="chat__empty-hint">
              Select an agent above for direct invocation, or leave on "Auto" to
              let the system route automatically.
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
              {msg.hitl ? (
                // date: 2026-08-17 dev: 陈子毅 changelog: AP4.6 渲染人机协同卡片（提问/选项/结论/超时降级）
                <HitlCard msg={msg} onAnswer={handleHitlAnswer} />
              ) : (
                <div className="chat__msg-content">
                  {msg.content || (msg.status === "sending" ? "Thinking..." : "")}
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
          placeholder="Type your message... (Enter to send, Shift+Enter for newline)"
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
          {isSending ? "Sending..." : streamMode ? "Stream" : "Send"}
        </button>
      </div>
    </div>
  );
}
