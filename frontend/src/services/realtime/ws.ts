// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/realtime/ws.ts，WebSocket 管理器：连接 /ws/v1/stream 并自动重连

import { useAppStore } from "@/mappers/store";
import type { ConnectionStatus, Message } from "@/protocol/types";

const DEFAULT_WS_URL = "ws://localhost:8000/ws/v1/stream";

function wsUrl(session?: string): string {
  const env = (import.meta.env.VITE_WS_URL as string | undefined) ?? "";
  const base = env.length > 0 ? env : DEFAULT_WS_URL;
  const qs = session
    ? `?session=${encodeURIComponent(session)}`
    : "";
  return `${base}${qs}`;
}

export type WsHandler = (message: Message) => void;

export class WsManager {
  private socket: WebSocket | null = null;
  private session: string | undefined;
  private handlers = new Set<WsHandler>();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;

  constructor(session?: string) {
    this.session = session;
  }

  setSession(session: string | undefined): void {
    this.session = session;
    if (this.socket) {
      this.reconnect();
    }
  }

  on(handler: WsHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  connect(): void {
    this.closed = false;
    this.open();
  }

  private open(): void {
    this.setStatus("connecting");
    const socket = new WebSocket(wsUrl(this.session));
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectDelay = 1000;
      this.setStatus("connected");
    };

    socket.onmessage = (msg) => {
      try {
        const message = JSON.parse(msg.data) as Message;
        this.dispatch(message);
      } catch {
        /* ignore malformed payloads */
      }
    };

    socket.onclose = () => {
      this.setStatus("disconnected");
      this.socket = null;
      if (!this.closed) {
        this.scheduleReconnect();
      }
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  send(message: Message): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
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

  reconnect(): void {
    this.socket?.close();
    this.socket = null;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.open();
  }

  private dispatch(message: Message): void {
    this.handlers.forEach((h) => h(message));
  }

  private setStatus(status: ConnectionStatus): void {
    useAppStore.getState().setConnectionStatus(status);
  }

  disconnect(): void {
    this.closed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.socket?.close();
    this.socket = null;
    this.setStatus("disconnected");
  }
}

export const wsManager = new WsManager();
