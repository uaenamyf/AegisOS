// date: 2026-07-03
// dev: Claude Code (glm-5.2)
// changelog: 导入源拆分——前端本地类型 Session 改从 @/protocol/frontend-types 引入（protocol 生成器剥离前端类型）

import { apiClient } from "@/lib/api-client";
import type { Session } from "@/protocol/frontend-types";

export interface CreateSessionRequest {
  user_id: string;
}

export const sessionApi = {
  create: (body: CreateSessionRequest = { user_id: "anonymous" }): Promise<Session> =>
    apiClient.post<Session>("/sessions", body),

  get: (id: string): Promise<Session> => apiClient.get<Session>(`/sessions/${id}`),

  close: (id: string): Promise<void> =>
    apiClient.del<void>(`/sessions/${id}`),
};
