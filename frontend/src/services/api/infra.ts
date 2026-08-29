// date: 2026-08-27
// dev: ox-alpha
// R11: 端边云基础设施 REST API 客户端 —— 消费 R10 后端 /api/v1/infra/* 端点

import { apiClient } from "@/lib/api-client";

export interface InfraNode {
  node_id: string;
  tier: "device" | "edge" | "cloud";
  status: string;  // "probe" | "online" | "offline"
  last_ok_ts: number;
  consecutive_failures: number;
  model_id: string;
  capabilities: string[];
  base_url?: string;
  /** API 厂商标签（DeepSeek / OpenAI / 火山方舟 / Ollama ...） */
  vendor?: string;
  /** 派生：status 非 offline 即在线 */
  online?: boolean;
  last_latency_ms?: number | null;
}

/** 后端 status → 前端 online 布尔 */
export function isOnline(node: InfraNode): boolean {
  return node.status !== "offline" && node.consecutive_failures < 2;
}

export interface DispatchResult {
  ok: boolean;
  text: string;
  tier: string;
  node_id: string;
  model_id: string;
  latency_ms: number;
  privacy_note: string;
  attempts: Array<{
    hop?: number;
    target_tier?: string;
    actual_tier?: string;
    tier?: string;
    ok: boolean;
    latency_ms: number;
    confidence?: number;
  }>;
}

export interface DispatchHistoryEntry extends DispatchResult {
  goal: string;
  privacy: string;
  timestamp: string;
}

export const infraApi = {
  /** 获取端边云节点列表 */
  listNodes(): Promise<InfraNode[]> {
    return apiClient.get<InfraNode[]>("/infra/nodes");
  },

  /** 派发任务 */
  dispatch(body: {
    goal: string;
    latency_budget?: number;
    privacy?: string;
    capability?: string;
    system_prompt?: string;
  }): Promise<DispatchResult> {
    return apiClient.post<DispatchResult>("/infra/dispatch", body);
  },

  /** 派发历史 */
  dispatchHistory(limit = 20): Promise<DispatchHistoryEntry[]> {
    return apiClient.get<DispatchHistoryEntry[]>(
      `/infra/dispatch/history?limit=${limit}`
    );
  },
};