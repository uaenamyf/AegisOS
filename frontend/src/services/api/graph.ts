// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/api/graph.ts，图 API 服务：get graph

import { apiClient } from "@/mappers/apimappers/client";
import type { Graph } from "@/protocol/types";

export const graphApi = {
  get: (): Promise<Graph> => apiClient.get<Graph>("/graph"),
};
