// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 views/layout/Sidebar.tsx，侧边导航 Canvas/Graph/Monitor/Replay

import { useAppStore } from "@/mappers/store";
import { ROUTES, routeController } from "@/controllers/routes";
import type { ViewName } from "@/protocol/types";

export function Sidebar() {
  const activeView = useAppStore((s) => s.activeView);
  const connectionStatus = useAppStore((s) => s.connectionStatus);

  const handleClick = (view: ViewName) => {
    routeController.goTo(view);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo">A</span>
        <span className="sidebar__title">AegisOS</span>
      </div>

      <nav className="sidebar__nav">
        {ROUTES.map((route) => (
          <button
            key={route.key}
            type="button"
            className={`sidebar__item${
              activeView === route.name ? " sidebar__item--active" : ""
            }`}
            onClick={() => handleClick(route.name)}
          >
            {route.label}
          </button>
        ))}
      </nav>

      <div className="sidebar__footer">
        <span
          className={`sidebar__status sidebar__status--${connectionStatus}`}
        />
        <span className="sidebar__status-label">{connectionStatus}</span>
      </div>
    </aside>
  );
}
