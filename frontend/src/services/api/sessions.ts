// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/api/sessions.ts，会话 API 服务：create/get/close

import { apiClient } from "@/mappers/apimappers/client";
import type { Session } from "@/protocol/types";

export interface CreateSessionRequest {
  trace_id?: string;
}

export const sessionApi = {
  create: (body: CreateSessionRequest = {}): Promise<Session> =>
    apiClient.post<Session>("/sessions", body),

  get: (id: string): Promise<Session> => apiClient.get<Session>(`/sessions/${id}`),

  close: (id: string): Promise<void> =>
    apiClient.post<void>(`/sessions/${id}/close`),
};
