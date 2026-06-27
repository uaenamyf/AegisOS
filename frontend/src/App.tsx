// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 App.tsx，主应用组件：侧边栏导航 + 主内容区按路由渲染

import { useEffect } from "react";
import { useAppStore } from "@/mappers/store";
import { Sidebar } from "@/views/layout";
import { CanvasView } from "@/views/canvas";
import { ChatView } from "@/views/chat";
import { GraphView } from "@/views/graph";
import { MonitorView } from "@/views/monitor";
import { ReplayView } from "@/views/replay";
import { eventController } from "@/controllers/events";
import { graphService } from "@/services/graph";
import { sessionService } from "@/services/session";
import type { ViewName } from "@/protocol/types";

const VIEWS: Record<ViewName, () => JSX.Element> = {
  canvas: CanvasView,
  chat: ChatView,
  graph: GraphView,
  monitor: MonitorView,
  replay: ReplayView,
};

export default function App() {
  const activeView = useAppStore((s) => s.activeView);

  useEffect(() => {
    eventController.start();
    const unsub = graphService.subscribe();
    void sessionService.createSession().catch(() => {
      /* backend may be offline during skeleton phase */
    });
    void graphService.fetch().catch(() => {
      /* graph fetch optional at boot */
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
