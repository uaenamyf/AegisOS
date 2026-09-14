// date: 2026-09-14
// dev: OpenSquilla
// changelog: R23 新建 chat API 服务——普通对话走后端真实推理，替代任务链固定 JSON

import { apiClient } from "@/lib/api-client";

export interface ChatResult {
  ok: boolean;
  intent: "chat" | "system_status" | "drill";
  error?: string;
  text: string;
  tier: string;
  node_id: string;
  model_id: string;
  provider: string;
  latency_ms: number;
  privacy_note: string;
  routed: boolean;
  attempts?: Array<Record<string, unknown>>;
}

export const chatApi = {
  send: (body: {
    goal: string;
    session_id?: string;
    history?: Array<{ role: string; content: string }>;
  }): Promise<ChatResult> => apiClient.post<ChatResult>("/chat", body),
};
