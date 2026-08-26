// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/api/graph.ts，图 API 服务：get graph

import { apiClient } from "@/lib/api-client";
import type { Graph } from "@/protocol/types";

export const graphApi = {
  get: (): Promise<Graph> => apiClient.get<Graph>("/graph"),
};
