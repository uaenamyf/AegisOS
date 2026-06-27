// @aegis-gen
// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// change: 新建 services/api/memory.ts，记忆 API 服务：read/write

import { apiClient } from "@/mappers/apimappers/client";
import type { MemoryPacket } from "@/protocol/types";

export const memoryApi = {
  read: (session: string): Promise<MemoryPacket> =>
    apiClient.get<MemoryPacket>(`/agents/memory/${encodeURIComponent(session)}`),

  write: (session: string, packet: MemoryPacket): Promise<MemoryPacket> =>
    apiClient.post<MemoryPacket>(
      `/agents/memory/${encodeURIComponent(session)}`,
      packet,
    ),
};
