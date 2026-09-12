import { useAppStore } from "@/lib/store";
import { ROUTES, routeController } from "@/controllers/routes";
import type { ViewName } from "@/protocol/frontend-types";

export function DemoSidebar() {
  const activeView = useAppStore((state) => state.activeView);
  const connectionStatus = useAppStore((state) => state.connectionStatus);
  const goTo = (view: ViewName) => routeController.goTo(view);

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo">A</span>
        <span className="sidebar__title">AegisOS</span>
      </div>
      <nav className="sidebar__nav">
        {ROUTES.map((route) => (
          <button key={route.key} type="button" className={`sidebar__item${activeView === route.name ? " sidebar__item--active" : ""}`} onClick={() => goTo(route.name)}>
            {route.label}
          </button>
        ))}
      </nav>
      <div className="sidebar__footer">
        <span className={`sidebar__status sidebar__status--${connectionStatus}`} />
        <span className="sidebar__status-label">{connectionStatus}</span>
      </div>
    </aside>
  );
}
