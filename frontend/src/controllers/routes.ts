// date: 2026-07-03
// dev: Claude Code (glm-5.2)
// changelog: 导入源拆分——前端本地类型 ViewName 改从 @/protocol/frontend-types 引入（protocol 生成器剥离前端类型）

import { useAppStore } from "@/lib/store";
import type { ViewName } from "@/protocol/frontend-types";

export const ROUTES: { name: ViewName; label: string; key: string }[] = [
  { name: "chat", label: "Chat", key: "chat" },
  { name: "canvas", label: "Canvas", key: "canvas" },
  { name: "graph", label: "Graph", key: "graph" },
  { name: "monitor", label: "Monitor", key: "monitor" },
  { name: "replay", label: "Replay", key: "replay" },
];

export const routeController = {
  goTo(view: ViewName): void {
    useAppStore.getState().setActiveView(view);
  },

  current(): ViewName {
    return useAppStore.getState().activeView;
  },
};
