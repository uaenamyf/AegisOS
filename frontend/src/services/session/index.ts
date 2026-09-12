// date: 2026-07-03
// dev: Claude Code (glm-5.2)
// changelog: 导入源拆分——Session 改从 @/protocol/frontend-types 引入，Task 仍从 @/protocol/types

import { sessionApi } from "@/services/api/sessions";
import { taskApi } from "@/services/api/tasks";
import { wsManager } from "@/services/realtime/ws";
import { useAppStore } from "@/lib/store";
import type { Session } from "@/protocol/frontend-types";
import type { Task } from "@/protocol/types";

export const sessionService = {
  async createSession(userId: string = "anonymous"): Promise<Session> {
    const session = await sessionApi.create({ user_id: userId });
    useAppStore.getState().setSession(session);
    try {
      localStorage.setItem("aegis.session_id", session.id);
    } catch {
      /* ignore storage errors */
    }
    wsManager.setSession(session.id);
    return session;
  },

  async loadSession(id: string): Promise<Session> {
    const session = await sessionApi.get(id);
    useAppStore.getState().setSession(session);
    wsManager.setSession(id);
    return session;
  },

  async closeSession(id: string): Promise<void> {
    await sessionApi.close(id);
    useAppStore.getState().setSession(null);
    wsManager.setSession(undefined);
    try {
      localStorage.removeItem("aegis.session_id");
    } catch {
      /* ignore storage errors */
    }
  },

  async refreshTasks(): Promise<Task[]> {
    const session = useAppStore.getState().currentSession;
    const tasks = await taskApi.list(session?.id);
    useAppStore.getState().setTasks(tasks);
    return tasks;
  },
};
