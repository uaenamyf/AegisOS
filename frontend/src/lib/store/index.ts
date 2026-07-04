// date: 2026-07-05
// dev: Claude Code (glm-5.2)
// changelog: 前端命名对齐后端——从 mappers/store/ 迁移至 lib/store/（对应后端 core/composition.py 的运行时状态职责）

import { create } from "zustand";
import type {
  Agent,
  Event,
  Graph,
  Task,
} from "@/protocol/types";
import type {
  ConnectionStatus,
  Session,
  ViewName,
} from "@/protocol/frontend-types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  agentId?: string;
  taskId?: string;
  status?: "sending" | "done" | "error";
  timestamp: number;
}

export interface AppState {
  currentSession: Session | null;
  tasks: Task[];
  agents: Agent[];
  graph: Graph;
  events: Event[];
  activeView: ViewName;
  connectionStatus: ConnectionStatus;
  chatMessages: ChatMessage[];
  isSending: boolean;
  selectedAgentId: string | null;

  setSession: (session: Session | null) => void;
  setTasks: (tasks: Task[]) => void;
  upsertTask: (task: Task) => void;
  setAgents: (agents: Agent[]) => void;
  upsertAgent: (agent: Agent) => void;
  setGraph: (graph: Graph) => void;
  applyGraph: (graph: Graph) => void;
  appendEvent: (event: Event) => void;
  setEvents: (events: Event[]) => void;
  setActiveView: (view: ViewName) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  addChatMessage: (msg: ChatMessage) => void;
  updateChatMessage: (id: string, patch: Partial<ChatMessage>) => void;
  clearChat: () => void;
  setSending: (sending: boolean) => void;
  setSelectedAgentId: (agentId: string | null) => void;
  reset: () => void;
}

const MAX_EVENTS = 500;

const initialState = {
  currentSession: null as Session | null,
  tasks: [] as Task[],
  agents: [] as Agent[],
  graph: { nodes: {}, edges: [] } as Graph,
  events: [] as Event[],
  activeView: "chat" as ViewName,
  connectionStatus: "disconnected" as ConnectionStatus,
  chatMessages: [] as ChatMessage[],
  isSending: false,
  selectedAgentId: null as string | null,
};

export const useAppStore = create<AppState>((set) => ({
  ...initialState,

  setSession: (session) => set({ currentSession: session }),

  setTasks: (tasks) => set({ tasks }),

  upsertTask: (task) =>
    set((state) => {
      const id = task.task_id ?? "";
      const idx = state.tasks.findIndex((t) => (t.task_id ?? "") === id);
      const tasks =
        idx >= 0
          ? state.tasks.map((t) => (t.task_id === id ? { ...t, ...task } : t))
          : [...state.tasks, task];
      return { tasks };
    }),

  setAgents: (agents) => set({ agents }),

  upsertAgent: (agent) =>
    set((state) => {
      const id = agent.agent_id;
      const idx = state.agents.findIndex((a) => a.agent_id === id);
      const agents =
        idx >= 0
          ? state.agents.map((a) =>
              a.agent_id === id ? { ...a, ...agent } : a,
            )
          : [...state.agents, agent];
      return { agents };
    }),

  setGraph: (graph) => set({ graph }),

  applyGraph: (graph) =>
    set((state) => ({
      graph: {
        nodes: { ...state.graph.nodes, ...(graph.nodes ?? {}) },
        edges: [...(state.graph.edges ?? []), ...(graph.edges ?? [])],
      },
    })),

  appendEvent: (event) =>
    set((state) => ({
      events: [...state.events, event].slice(-MAX_EVENTS),
    })),

  setEvents: (events) => set({ events }),

  setActiveView: (view) => set({ activeView: view }),

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  addChatMessage: (msg) =>
    set((state) => ({ chatMessages: [...state.chatMessages, msg] })),

  updateChatMessage: (id, patch) =>
    set((state) => ({
      chatMessages: state.chatMessages.map((m) =>
        m.id === id ? { ...m, ...patch } : m,
      ),
    })),

  clearChat: () => set({ chatMessages: [] }),

  setSending: (sending) => set({ isSending: sending }),

  setSelectedAgentId: (agentId) => set({ selectedAgentId: agentId }),

  reset: () => set({ ...initialState }),
}));
