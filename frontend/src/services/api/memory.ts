// date: 2026-06-27
// dev: Claude Code (glm-5.2)
// changelog: 新建 services/api/memory.ts，记忆 API 服务：read/write
// changelog: 2026-09-13 R-mem 新增 stats——记忆子系统统计（供 Monitor 记忆面板）

import { apiClient } from "@/lib/api-client";
import type { MemoryPacket } from "@/protocol/types";

export interface MemoryStats {
  working_sessions: number;
  episodic_total: number;
  semantic_total: number;
  vector_total: number;
  archive_total: number;
  checkpoint_total: number;
  snapshot_total: number;
  persisted: boolean;
  auto_embed: boolean;
  recent_decisions: Array<Record<string, unknown>>;
}

export const memoryApi = {
  read: (session: string): Promise<MemoryPacket> =>
    apiClient.get<MemoryPacket>(`/memory/${encodeURIComponent(session)}`),

  write: (session: string, packet: MemoryPacket): Promise<MemoryPacket> =>
    apiClient.post<MemoryPacket>(
      `/memory/${encodeURIComponent(session)}`,
      packet,
    ),

  stats: (): Promise<MemoryStats> =>
    apiClient.get<MemoryStats>(`/memory/stats`),
};
