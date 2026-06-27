// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 controllers/events.ts，后端事件控制器：订阅 SSE 并分发到 store

import { sseManager, wsManager } from "@/services/realtime";
import { useAppStore } from "@/mappers/store";
import type { Agent, Event, Task } from "@/protocol/types";

export const eventController = {
  start(): void {
    sseManager.connect();
    wsManager.connect();

    sseManager.on((event: Event) => {
      switch (event.event_type) {
        case "agent.start":
        case "agent.finish": {
          const agent = event.payload?.agent as Agent | undefined;
          if (agent?.agent_id) {
            useAppStore.getState().upsertAgent(agent);
          }
          break;
        }
        case "task.retry":
        case "task.rollback": {
          const task = event.payload?.task as Task | undefined;
          if (task?.task_id) {
            useAppStore.getState().upsertTask(task);
          }
          break;
        }
        default:
          break;
      }
    });
  },

  stop(): void {
    sseManager.disconnect();
    wsManager.disconnect();
  },
};
