// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 controllers/routes.ts，路由控制器：视图切换 canvas/graph/monitor/replay

import { useAppStore } from "@/mappers/store";
import type { ViewName } from "@/protocol/types";

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
