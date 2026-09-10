// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/api/tasks.ts，任务 API 服务：create/list/get/cancel

import { apiClient } from "@/lib/api-client";
import type { Task } from "@/protocol/types";

export interface CreateTaskRequest {
  goal: string;
  session_id?: string;
  plan?: Record<string, unknown>;
  dependency?: string[];
  priority?: number;
  payload?: Record<string, unknown>;
}

/** 兼容旧 API barrel 的包装响应类型；当前后端列表接口实际返回 Task 数组。 */
export interface ListTasksResponse {
  tasks: Task[];
}

export const taskApi = {
  create: (body: CreateTaskRequest): Promise<Task> =>
    apiClient.post<Task>("/tasks", body),

  list: (sessionId?: string): Promise<Task[]> => {
    const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return apiClient.get<Task[]>(`/tasks${qs}`).then((tasks) => tasks ?? []);
  },

  get: (id: string): Promise<Task> => apiClient.get<Task>(`/tasks/${id}`),

  cancel: (id: string): Promise<Task> =>
    apiClient.post<Task>(`/tasks/${id}/cancel`),
};
