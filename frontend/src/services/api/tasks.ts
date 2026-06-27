// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/api/tasks.ts，任务 API 服务：create/list/get/cancel

import { apiClient } from "@/mappers/apimappers/client";
import type { Task } from "@/protocol/types";

export interface CreateTaskRequest {
  goal: string;
  session_id?: string;
  plan?: Record<string, unknown>;
  dependency?: string[];
  priority?: number;
}

export interface ListTasksResponse {
  tasks: Task[];
}

export const taskApi = {
  create: (body: CreateTaskRequest): Promise<Task> =>
    apiClient.post<Task>("/tasks", body),

  list: (sessionId?: string): Promise<Task[]> => {
    const qs = sessionId ? `?session=${encodeURIComponent(sessionId)}` : "";
    return apiClient
      .get<ListTasksResponse>(`/tasks${qs}`)
      .then((r) => r.tasks ?? []);
  },

  get: (id: string): Promise<Task> => apiClient.get<Task>(`/tasks/${id}`),

  cancel: (id: string): Promise<Task> =>
    apiClient.post<Task>(`/tasks/${id}/cancel`),
};
