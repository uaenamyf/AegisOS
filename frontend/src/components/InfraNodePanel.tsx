// date: 2026-08-27
// dev: ox-alpha
// R11: 端边云节点面板 —— 三张卡片展示 device/edge/cloud 在线状态

import { useEffect, useState } from "react";
import { infraApi, type InfraNode } from "@/services/api/infra";

const TIER_LABELS: Record<string, string> = {
  device: "端 (Device)",
  edge: "边 (Edge)",
  cloud: "云 (Cloud)",
};

const TIER_ICONS: Record<string, string> = {
  device: "🖥️",
  edge: "🌐",
  cloud: "☁️",
};

const TIER_COLORS: Record<string, string> = {
  device: "#3fb950",
  edge: "#2f81f7",
  cloud: "#d29922",
};

export function InfraNodePanel() {
  const [nodes, setNodes] = useState<InfraNode[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetch = async () => {
      try {
        const data = await infraApi.listNodes();
        if (!cancelled) {
          setNodes(data);
          setError(null);
        }
      } catch {
        if (!cancelled) setError("后端未连接");
      }
    };

    fetch();
    const interval = setInterval(fetch, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="infra-panel">
      <h3 className="infra-panel__title">端边云节点</h3>
      {error && <p className="infra-panel__error">{error}</p>}
      <div className="infra-panel__cards">
        {(["device", "edge", "cloud"] as const).map((tier) => {
          const node = nodes.find((n) => n.tier === tier);
          const online = node?.online ?? false;
          return (
            <div
              key={tier}
              className={`infra-card ${online ? "infra-card--online" : "infra-card--offline"}`}
              style={{ borderColor: TIER_COLORS[tier] }}
            >
              <div className="infra-card__icon">{TIER_ICONS[tier]}</div>
              <div className="infra-card__label">{TIER_LABELS[tier]}</div>
              <div className="infra-card__status">
                <span
                  className={`infra-card__dot ${online ? "infra-card__dot--ok" : "infra-card__dot--dead"}`}
                />
                {online ? "在线" : "离线"}
              </div>
              {node?.last_latency_ms != null && (
                <div className="infra-card__latency">
                  {node.last_latency_ms.toFixed(0)} ms
                </div>
              )}
              {node?.node_id && (
                <div className="infra-card__id">{node.node_id}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}