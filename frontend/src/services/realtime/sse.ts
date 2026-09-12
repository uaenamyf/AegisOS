// date: 2026-09-12
// changelog: 修复全局 SSE 收不到任何事件的致命 Bug——后端发命名事件（event: <topic>），
// onmessage 只能收无名 message 帧；改为按已知主题 addEventListener 逐一分发。

import { config } from "@/config";
import { useAppStore } from "@/lib/store";
import type { ConnectionStatus } from "@/protocol/frontend-types";
import type { Event } from "@/protocol/types";

function sseUrl(): string {
  return config.sseUrl;
}

/** 后端事件总线会经 /events 推送的全部主题（锚点：protocol/event.py EventType） */
const SSE_TOPICS = [
  "agent.start",
  "agent.finish",
  "tool.call",
  "tool.finish",
  "task.retry",
  "task.rollback",
  "memory.update",
  "graph.update",
  "human.input.required",
  "human.response",
  "node.status_change",
  "drill.round",
  "drill.agent",
  "drill.status",
] as const;

export type SseHandler = (event: Event) => void;

export class SseManager {
  private source: EventSource | null = null;
  private stream: string;
  private handlers = new Set<SseHandler>();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;

  constructor(stream = "all") {
    this.stream = stream;
  }

  on(handler: SseHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  connect(): void {
    this.closed = false;
    this.open();
  }

  private open(): void {
    const url = `${sseUrl()}?stream=${encodeURIComponent(this.stream)}&api_key=${config.apiKey}`;
    this.setStatus("connecting");
    const source = new EventSource(url);
    this.source = source;

    source.onopen = () => {
      this.reconnectDelay = 1000;
      this.setStatus("connected");
    };

    // 命名事件分发：后端以 event: <topic> 帧推送，必须按主题监听。
    // onmessage 只收无名 message 帧——这是此前全局事件全部丢失的根因。
    const envelope = (topic: string) => (msg: MessageEvent) => {
      try {
        const data = JSON.parse(msg.data) as Record<string, any>;
        // 事件总线载体是 protocol.Event（event_type 为枚举值）；统一归一化为
        // 前端 Event 形状：event_type = topic 字符串，payload = 载体 payload
        const event: Event = {
          event_id: typeof data.event_id === "string" ? data.event_id : undefined,
          event_type: topic,
          task_id: typeof data.task_id === "string" ? data.task_id : undefined,
          payload: (data.payload ?? {}) as Record<string, any>,
          timestamp: typeof data.timestamp === "number" ? data.timestamp : undefined,
        };
        this.dispatch(event);
      } catch {
        /* ignore malformed payloads */
      }
    };
    for (const topic of SSE_TOPICS) {
      source.addEventListener(topic, envelope(topic) as EventListener);
    }

    source.onerror = () => {
      this.setStatus("disconnected");
      source.close();
      this.source = null;
      if (!this.closed) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const delay = this.reconnectDelay;
    this.reconnectDelay = Math.min(
      this.reconnectDelay * 2,
      this.maxReconnectDelay,
    );
    this.reconnectTimer = setTimeout(() => this.open(), delay);
  }

  private dispatch(event: Event): void {
    useAppStore.getState().appendEvent(event);
    this.handlers.forEach((h) => h(event));
  }

  private setStatus(status: ConnectionStatus): void {
    useAppStore.getState().setConnectionStatus(status);
  }

  disconnect(): void {
    this.closed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.source?.close();
    this.source = null;
    this.setStatus("disconnected");
  }
}

export const sseManager = new SseManager("all");
