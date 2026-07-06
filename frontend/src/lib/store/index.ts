// date: 2026-07-05
// dev: Claude Code (glm-5.2)
// changelog: 前端命名对齐后端——从 mappers/store/ 迁移至 lib/store/（对应后端 core/composition.py 的运行时状态职责）

import { create } from "zustand";
import type {
  Agent,
  Event,
  Graph,
  Task,
  BlueDefenseResponse,
  PurpleReviewResponse,
  RangeResponse,
  RedAttackResponse,
  ThreatIntel,
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

  // date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 新增攻防演练状态字段
  currentRange: RangeResponse | null;
  redAttackResult: RedAttackResponse | null;
  blueDefenseResult: BlueDefenseResponse | null;
  purpleReviewResult: PurpleReviewResponse | null;
  threatIntel: ThreatIntel[];
  cyberLoading: boolean;
  cyberError: string | null;

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

  // date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 新增攻防演练 setter
  setCurrentRange: (range: RangeResponse | null) => void;
  setRedAttackResult: (result: RedAttackResponse | null) => void;
  setBlueDefenseResult: (result: BlueDefenseResponse | null) => void;
  setPurpleReviewResult: (result: PurpleReviewResponse | null) => void;
  setThreatIntel: (intel: ThreatIntel[]) => void;
  setCyberLoading: (loading: boolean) => void;
  setCyberError: (error: string | null) => void;

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
  // date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 攻防演练初始状态
  currentRange: null as RangeResponse | null,
  redAttackResult: null as RedAttackResponse | null,
  blueDefenseResult: null as BlueDefenseResponse | null,
  purpleReviewResult: null as PurpleReviewResponse | null,
  threatIntel: [] as ThreatIntel[],
  cyberLoading: false,
  cyberError: null as string | null,
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

  // date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 攻防演练 setter 实现
  setCurrentRange: (range) => set({ currentRange: range }),
  setRedAttackResult: (result) => set({ redAttackResult: result }),
  setBlueDefenseResult: (result) => set({ blueDefenseResult: result }),
  setPurpleReviewResult: (result) => set({ purpleReviewResult: result }),
  setThreatIntel: (intel) => set({ threatIntel: intel }),
  setCyberLoading: (loading) => set({ cyberLoading: loading }),
  setCyberError: (error) => set({ cyberError: error }),

  reset: () => set({ ...initialState }),
}));
