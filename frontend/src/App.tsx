// date: 2026-07-04
// dev: Claude Code (glm-5.2)
// changelog: 启动时拉取 Agent 列表填充 store.agents（agentApi.list → setAgents），失败静默忽略

import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { Sidebar } from "@/views/layout";
import { CanvasView } from "@/views/canvas";
import { ChatView } from "@/views/chat";
import { CyberView } from "@/views/cyber";
import { DrillHistoryView } from "@/views/drill-history";
import { GraphView } from "@/views/graph";
import { MonitorView } from "@/views/monitor";
import { ReplayView } from "@/views/replay";
import { SettingsView } from "@/views/settings";
import { eventController } from "@/controllers/events";
import { agentApi } from "@/services/api/agents";
import { taskApi } from "@/services/api/tasks";
import { graphService } from "@/services/graph";
import { sessionService } from "@/services/session";
import type { ViewName } from "@/protocol/frontend-types";

const VIEWS: Record<ViewName, () => JSX.Element> = {
  canvas: CanvasView,
  chat: ChatView,
  cyber: CyberView,
  "drill-history": DrillHistoryView,
  graph: GraphView,
  monitor: MonitorView,
  replay: ReplayView,
  settings: SettingsView,
};

export default function App() {
  const activeView = useAppStore((s) => s.activeView);

  useEffect(() => {
    eventController.start();
    const unsub = graphService.subscribe();
    void sessionService
      .createSession()
      .then((session) => taskApi.list(session.id))
      .then((tasks) => useAppStore.getState().setTasks(tasks))
      .catch(() => {
        /* backend may be offline during skeleton phase */
      });
    void graphService.fetch().catch(() => {
      /* graph fetch optional at boot */
    });
    void agentApi
      .list()
      .then((agents) => useAppStore.getState().setAgents(agents))
      .catch(() => {
        /* agent list fetch optional at boot */
      });
    return () => {
      unsub();
      eventController.stop();
    };
  }, []);

  const ActiveView = VIEWS[activeView] ?? CanvasView;

  return (
    <div className="app">
      <Sidebar />
      <main className="app__main">
        <ActiveView />
      </main>
    </div>
  );
}
