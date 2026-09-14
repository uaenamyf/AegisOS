// date: 2026-07-03
// dev: Claude Code (glm-5.2)
// changelog: 导入源拆分——前端本地类型 ViewName 改从 @/protocol/frontend-types 引入（protocol 生成器剥离前端类型）

import { useAppStore } from "@/lib/store";
import type { ViewName } from "@/protocol/frontend-types";

export const ROUTES: { name: ViewName; label: string; key: string }[] = [
  { name: "chat", label: "Chat", key: "chat" },
  // date: 2026-09-14 dev: OpenSquilla changelog: R21 —— Graph+Canvas 合并为任务图 TaskMap（Chat/Cyber 双模式切换）
  { name: "taskmap", label: "Task Map", key: "taskmap" },
  { name: "monitor", label: "Monitor", key: "monitor" },
  // date: 2026-09-14 dev: OpenSquilla changelog: R21 —— Replay 移除，历史回顾统一到「演练历史」
  // date: 2026-07-06 dev: Claude Code (glm-5.2) changelog: 新增 cyber 攻防演练路由
  { name: "cyber", label: "Cyber Defense", key: "cyber" },
  { name: "drill-history", label: "演练历史", key: "drill-history" },
  { name: "settings", label: "运行配置", key: "settings" },
];

export const routeController = {
  goTo(view: ViewName): void {
    useAppStore.getState().setActiveView(view);
  },

  current(): ViewName {
    return useAppStore.getState().activeView;
  },
};
