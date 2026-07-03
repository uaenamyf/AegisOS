// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 ChatView，用户与智能体对话的聊天界面

import { useState, useRef, useEffect, useCallback } from "react";
import { useAppStore, type ChatMessage } from "@/mappers/store";
import { agentApi } from "@/services/api/agents";
import { taskApi } from "@/services/api/tasks";

function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
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
              <div className="chat__msg-content">
                {msg.content || (msg.status === "sending" ? "Thinking..." : "")}
              </div>
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
          onClick={() => void handleSend()}
          disabled={!input.trim() || isSending}
        >
          {isSending ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
