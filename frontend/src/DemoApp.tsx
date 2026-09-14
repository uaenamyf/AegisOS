import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { DemoSidebar } from "@/views/layout/DemoSidebar";
import { ChatView } from "@/views/chat";
import { CyberView } from "@/views/cyber";
import { DrillHistoryView } from "@/views/drill-history";
import { MonitorView } from "@/views/monitor";
import { DemoSettingsView } from "@/views/settings/DemoSettingsView";
import { TaskMapView } from "@/views/taskmap";
import { eventController } from "@/controllers/events";
import { agentApi } from "@/services/api/agents";
import { graphService } from "@/services/graph";
import { sessionService } from "@/services/session";
import type { ViewName } from "@/protocol/frontend-types";

const VIEWS: Record<ViewName, () => JSX.Element> = {
  chat: ChatView,
  taskmap: TaskMapView,
  cyber: CyberView,
  "drill-history": DrillHistoryView,
  monitor: MonitorView,
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
