// date: 2026-07-04
// dev: Claude Code (glm-5.2)
// changelog: 接入统一配置——SSE URL/apiKey 改从 @/config 读取

import { config } from "@/config";
import { useAppStore } from "@/lib/store";
import type { ConnectionStatus } from "@/protocol/frontend-types";
import type { Event } from "@/protocol/types";

function sseUrl(): string {
  return config.sseUrl;
}

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

    source.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as Event;
        this.dispatch(event);
      } catch {
        /* ignore malformed payloads */
      }
    };

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
