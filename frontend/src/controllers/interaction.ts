// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 controllers/interaction.ts，用户交互控制器：任务创建/Agent 调用/视图切换

import { taskApi } from "@/services/api/tasks";
import type { CreateTaskRequest } from "@/services/api/tasks";
import { agentApi } from "@/services/api/agents";
import { sessionService } from "@/services/session";
import { useAppStore } from "@/mappers/store";
import type { ViewName } from "@/protocol/types";

export const interactionController = {
  async createTask(request: CreateTaskRequest) {
    const task = await taskApi.create(request);
    useAppStore.getState().upsertTask(task);
    return task;
  },

  async cancelTask(taskId: string) {
    const task = await taskApi.cancel(taskId);
    useAppStore.getState().upsertTask(task);
    return task;
  },

  async invokeTool(toolName: string, args?: Record<string, unknown>) {
    return agentApi.invokeTool(toolName, { name: toolName, args: args ?? {} });
  },

  switchView(view: ViewName) {
    useAppStore.getState().setActiveView(view);
  },

  async ensureSession(): Promise<void> {
    const store = useAppStore.getState();
    if (store.currentSession) return;
    await sessionService.createSession();
  },
};
