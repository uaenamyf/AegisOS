import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { DemoSidebar } from "@/views/layout/DemoSidebar";
import { CanvasView } from "@/views/canvas";
import { ChatView } from "@/views/chat";
import { CyberView } from "@/views/cyber";
import { GraphView } from "@/views/graph";
import { MonitorView } from "@/views/monitor";
import { ReplayView } from "@/views/replay";
import { DemoSettingsView } from "@/views/settings/DemoSettingsView";
import { DrillHistoryView } from "@/views/drill-history";
import { eventController } from "@/controllers/events";
import { agentApi } from "@/services/api/agents";
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
  settings: DemoSettingsView,
};

export default function DemoApp() {
  const activeView = useAppStore((state) => state.activeView);

  useEffect(() => {
    eventController.start();
    const unsubscribe = graphService.subscribe();
    void sessionService.createSession().catch(() => undefined);
    void graphService.fetch().catch(() => undefined);
    void agentApi.list().then((agents) => useAppStore.getState().setAgents(agents)).catch(() => undefined);
    return () => {
      unsubscribe();
      eventController.stop();
    };
  }, []);

  const ActiveView = VIEWS[activeView] ?? ChatView;
  return <div className="app"><DemoSidebar /><main className="app__main"><ActiveView /></main></div>;
}
