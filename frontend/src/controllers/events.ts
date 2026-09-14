// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 controllers/events.ts，后端事件控制器：订阅 SSE 并分发到 store

import { sseManager, wsManager } from "@/services/realtime";
import { taskApi } from "@/services/api/tasks";
import {
  handleAgentActivityEvent,
  resetStaleActivity,
} from "@/services/agentActivity";
import { useAppStore, type HitlPayload } from "@/lib/store";
import type { Agent, Event, Task } from "@/protocol/types";

// date: 2026-08-17
// dev: 陈子毅
// changelog: AP4.6 新增 HITL 卡片消息 id 生成器
function hitlId(): string {
  return `hitl-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const eventController = {
  start(): void {
    sseManager.connect();
    wsManager.connect();

    // 断线自愈：后端重连成功后，清掉后端崩溃期间遗留的"Agent 执行中"
    // 僵尸状态（其结束事件永远不会再来）
    sseManager.onReconnected(() => resetStaleActivity());

    sseManager.on((event: Event) => {
      const refreshTasks = () => {
        const sessionId = useAppStore.getState().currentSession?.id;
        if (sessionId) {
          void taskApi.list(sessionId).then((tasks) => useAppStore.getState().setTasks(tasks)).catch(() => {});
        }
      };
      switch (event.event_type) {
        case "agent.start":
        case "agent.finish": {
          const agent = event.payload?.agent as Agent | undefined;
          if (agent?.agent_id) {
            useAppStore.getState().upsertAgent(agent);
          }
          refreshTasks();
          break;
        }
        case "task.retry":
        case "task.rollback": {
          const task = event.payload?.task as Task | undefined;
          if (task?.task_id) {
            useAppStore.getState().upsertTask(task);
          }
          refreshTasks();
          break;
        }
        case "drill.round": {
          refreshTasks();
          break;
        }
        // CoT/ToT 可视化 + Monitor 活跃状态：演练 agent 级事件与状态变更
        case "drill.agent":
        case "drill.status": {
          handleAgentActivityEvent(event.event_type, event.payload);
          break;
        }
        // date: 2026-08-17
        // dev: 陈子毅
        // changelog: AP4.6 渲染人机协同卡片——订阅 HumanInputRequired / HumanResponse 事件
        case "human.input.required": {
          const p = (event.payload ?? {}) as Record<string, any>;
          const agent =
            (event.source?.node_id as string) ||
            (p.agent as string) ||
            "Agent";
          useAppStore.getState().addChatMessage({
            id: hitlId(),
            role: "assistant",
            content: "",
            agentId: agent,
            taskId: event.task_id,
            timestamp: Date.now(),
            hitl: {
              kind: "request",
              status: "pending",
              agent,
              taskId: event.task_id,
              question: p.question as string,
              options: (p.options as string[]) ?? [],
              context: (p.context as Record<string, any>) ?? {},
            },
          });
          break;
        }
        case "human.response": {
          const p = (event.payload ?? {}) as Record<string, any>;
          const agent =
            (event.source?.node_id as string) ||
            (p.agent as string) ||
            "Agent";
          const store = useAppStore.getState();
          // 关联到同一 task 的最新未决请求卡片，原位更新为已处理（单卡片演进）
          const pending = [...store.chatMessages]
            .reverse()
            .find(
              (m) =>
                m.hitl?.kind === "request" &&
                m.hitl.status === "pending" &&
                (m.hitl.taskId ?? "") === (event.task_id ?? ""),
            );
          const resolution: HitlPayload = {
            kind: "resolved",
            status: "resolved",
            agent,
            taskId: event.task_id,
            question: pending?.hitl?.question,
            options: pending?.hitl?.options ?? [],
            answer: p.answer as string,
            answered: Boolean(p.answered),
            timeout: Boolean(p.timeout),
            rationale: p.rationale as string,
          };
          if (pending) {
            store.updateChatMessage(pending.id, { hitl: resolution });
          } else {
            store.addChatMessage({
              id: hitlId(),
              role: "assistant",
              content: "",
              agentId: agent,
              taskId: event.task_id,
              timestamp: Date.now(),
              hitl: resolution,
            });
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
