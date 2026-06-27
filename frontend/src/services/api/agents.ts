// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/api/agents.ts，Agent API 服务：list/get/invokeAgent/invokeTool
// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 修复 invoke 端点——invokeAgent 调 POST /agents/{id}/invoke；原 invoke 改名 invokeTool

import { apiClient } from "@/mappers/apimappers/client";
import type { Agent, ToolResult } from "@/protocol/types";

export interface InvokeAgentRequest {
  goal: string;
  session_id: string;
}

export interface InvokeAgentResponse {
  agent_id: string;
  result: {
    agent_id: string;
    task_id: string;
    status: string;
    output: string;
  };
}

export interface InvokeToolRequest {
  name: string;
  args: Record<string, unknown>;
}

export interface ListAgentsResponse {
  agents: Agent[];
}

export const agentApi = {
  list: (): Promise<Agent[]> =>
    apiClient
      .get<ListAgentsResponse>("/agents")
      .then((r) => r.agents ?? []),

  get: (id: string): Promise<Agent> => apiClient.get<Agent>(`/agents/${id}`),

  invokeAgent: (agentId: string, body: InvokeAgentRequest): Promise<InvokeAgentResponse> =>
    apiClient.post<InvokeAgentResponse>(`/agents/${encodeURIComponent(agentId)}/invoke`, body),

  invokeTool: (toolName: string, body: InvokeToolRequest): Promise<ToolResult> =>
    apiClient.post<ToolResult>(`/tools/${encodeURIComponent(toolName)}/invoke`, body),
};
