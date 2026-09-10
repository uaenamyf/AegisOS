// date: 2026-07-07
// dev: myf
// changelog: R5.3 新建流式 API 服务——fetch + ReadableStream 读取 POST SSE，实时返回 Agent 执行事件

import { config } from "@/config";

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export type StreamHandler = (event: StreamEvent) => void;

/**
 * 流式执行指定 Agent，逐事件回调。
 * R5.3：用 fetch POST + ReadableStream 读取 SSE 帧。
 *
 * @param agentId 目标 Agent ID
 * @param prompt 用户 prompt
 * @param onEvent 事件回调
 * @returns AbortController（用于取消流式）
 */
export async function streamAgent(
  agentId: string,
  prompt: string,
  onEvent: StreamHandler,
): Promise<AbortController> {
  const controller = new AbortController();
  const url = `${config.apiBaseUrl}/stream/agent/${agentId}`;

  await (async () => {
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        onEvent({ event: "error", data: { error: `HTTP ${resp.status}` } });
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "message";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割 SSE 帧
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                onEvent({ event: currentEvent, data });
              } catch {
                // 忽略解析失败的帧
              }
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        onEvent({ event: "error", data: { error: err.message } });
      }
    }
  })();

  return controller;
}

/**
 * 流式执行红队攻击链，逐步回调。
 */
export async function streamRedChain(
  targetRange: string,
  onEvent: StreamHandler,
): Promise<AbortController> {
  const controller = new AbortController();
  const url = `${config.apiBaseUrl}/stream/red_chain`;

  void (async () => {
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_range: targetRange }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        onEvent({ event: "error", data: { error: `HTTP ${resp.status}` } });
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "message";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                onEvent({ event: currentEvent, data });
              } catch {
                // ignore
              }
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        onEvent({ event: "error", data: { error: err.message } });
      }
    }
  })();

  return controller;
}
