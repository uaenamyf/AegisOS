// date: 2026-09-04
// dev: AegisOS Dev
// changelog: R4 新建 cyberApi drill 方法单测（mock apiClient + mock EventSource 验证 SSE 分发）

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock apiClient before importing cyberApi
vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";
import { cyberApi } from "@/services/api/cyber";
import { config } from "@/config";
import type { DrillEvent } from "@/protocol/types";

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cyberApi.startDrill", () => {
  it("POSTs to /drill/start with body", async () => {
    const fake = {
      drill_id: "drill-abc",
      status: "running",
      max_rounds: 5,
    };
    mockPost.mockResolvedValue(fake);

    const result = await cyberApi.startDrill({
      target_range: "10.0.0.0/24",
      max_rounds: 3,
    });

    expect(mockPost).toHaveBeenCalledWith("/drill/start", {
      target_range: "10.0.0.0/24",
      max_rounds: 3,
    });
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.getDrill", () => {
  it("GETs /drill/{id}", async () => {
    const fake = {
      drill_id: "drill-abc",
      target_range: "10.0.0.0/24",
      max_rounds: 5,
      rounds_executed: 3,
      convergence_code: "converged",
      rounds: [],
      summary: { conclusion: "ok", convergence_code: "converged", rounds_executed: 3 },
    };
    mockGet.mockResolvedValue(fake);

    const result = await cyberApi.getDrill("drill-abc");

    expect(mockGet).toHaveBeenCalledWith("/drill/drill-abc");
    expect(result.convergence_code).toBe("converged");
  });

  it("encodes special characters in drill ID", async () => {
    mockGet.mockResolvedValue({});
    await cyberApi.getDrill("drill/with spaces");
    expect(mockGet).toHaveBeenCalledWith("/drill/drill%2Fwith%20spaces");
  });
});

describe("cyberApi.getDrillSummary", () => {
  it("GETs /drill/{id}/summary", async () => {
    const fake = {
      conclusion: "演练收敛",
      convergence_code: "converged",
      rounds_executed: 3,
    };
    mockGet.mockResolvedValue(fake);

    const result = await cyberApi.getDrillSummary("drill-abc");

    expect(mockGet).toHaveBeenCalledWith("/drill/drill-abc/summary");
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.abortDrill", () => {
  it("POSTs to /drill/{id}/abort", async () => {
    mockPost.mockResolvedValue({ drill_id: "drill-abc", status: "aborted" });

    const result = await cyberApi.abortDrill("drill-abc");

    expect(mockPost).toHaveBeenCalledWith("/drill/drill-abc/abort");
    expect(result.status).toBe("aborted");
  });
});

describe("cyberApi.openDrillStream", () => {
  class FakeEventSource {
    static instances: FakeEventSource[] = [];
    url: string;
    listeners: Record<string, ((msg: { data: string }) => void)[]> = {};
    closed = false;

    constructor(url: string) {
      this.url = url;
      FakeEventSource.instances.push(this);
    }

    addEventListener(name: string, cb: (msg: { data: string }) => void): void {
      this.listeners[name] = this.listeners[name] || [];
      this.listeners[name].push(cb);
    }

    close(): void {
      this.closed = true;
    }
  }

  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  it("connects to /drill/{id}/stream with api_key query", () => {
    cyberApi.openDrillStream("drill-abc", () => {});

    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0].url).toBe(
      `${config.apiBaseUrl}/drill/drill-abc/stream?api_key=${encodeURIComponent(config.apiKey)}`,
    );
  });

  it("dispatches named events to onEvent by event name", () => {
    const received: DrillEvent[] = [];
    const close = cyberApi.openDrillStream("drill-abc", (ev) => received.push(ev));
    const src = FakeEventSource.instances[0];

    const round = { round: 1, red: { ok: true }, convergence_code: "continue" };
    src.listeners["drill_round"].forEach((cb) =>
      cb({ data: JSON.stringify(round) }),
    );
    src.listeners["drill_done"].forEach((cb) =>
      cb({ data: JSON.stringify({ drill_id: "drill-abc" }) }),
    );

    expect(received).toEqual([
      { name: "drill_round", data: round },
      { name: "drill_done", data: { drill_id: "drill-abc" } },
    ]);

    // 返回的关闭函数应关闭 EventSource
    close();
    expect(src.closed).toBe(true);
  });

  it("ignores malformed payloads", () => {
    const received: DrillEvent[] = [];
    cyberApi.openDrillStream("drill-abc", (ev) => received.push(ev));
    const src = FakeEventSource.instances[0];

    src.listeners["drill_round"].forEach((cb) => cb({ data: "{not-json" }));
    expect(received).toEqual([]);
  });
});
