// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 G6 cyber API service 单元测试（mock apiClient + 断言调用参数与返回值）

import { describe, it, expect, vi, beforeEach } from "vitest";

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

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("cyberApi.startRange", () => {
  it("POSTs to /range/start with body", async () => {
    const fake = { range_id: "range-abc", target_range: "10.0.0.0/24", label: "test", status: "active", topology: { target_range: "10.0.0.0/24", nodes: [], edges: [] } };
    mockPost.mockResolvedValue(fake);

    const result = await cyberApi.startRange({ target_range: "10.0.0.0/24" });

    expect(mockPost).toHaveBeenCalledWith("/range/start", { target_range: "10.0.0.0/24" });
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.getRange", () => {
  it("GETs /range/{id}", async () => {
    const fake = { range_id: "range-abc", target_range: "10.0.0.0/24", label: "", status: "active", topology: { target_range: "", nodes: [], edges: [] } };
    mockGet.mockResolvedValue(fake);

    const result = await cyberApi.getRange("range-abc");

    expect(mockGet).toHaveBeenCalledWith("/range/range-abc");
    expect(result.range_id).toBe("range-abc");
  });

  it("encodes special characters in range ID", async () => {
    mockGet.mockResolvedValue({});
    await cyberApi.getRange("range/with spaces");
    expect(mockGet).toHaveBeenCalledWith("/range/range%2Fwith%20spaces");
  });
});

describe("cyberApi.getTopology", () => {
  it("GETs /range/{id}/topology", async () => {
    const fake = { target_range: "10.0.0.0/24", nodes: [], edges: [] };
    mockGet.mockResolvedValue(fake);

    const result = await cyberApi.getTopology("range-abc");
    expect(mockGet).toHaveBeenCalledWith("/range/range-abc/topology");
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.redAttack", () => {
  it("POSTs to /attack", async () => {
    const fake = { assets: [], findings: [], chain: {} };
    mockPost.mockResolvedValue(fake);

    const result = await cyberApi.redAttack({ target_range: "10.0.0.0/24" });
    expect(mockPost).toHaveBeenCalledWith("/attack", { target_range: "10.0.0.0/24" });
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.getAttackChain", () => {
  it("GETs /attack/chain/{id}", async () => {
    mockGet.mockResolvedValue({ assets: [], findings: [], chain: {} });
    await cyberApi.getAttackChain("range-abc");
    expect(mockGet).toHaveBeenCalledWith("/attack/chain/range-abc");
  });
});

describe("cyberApi.blueDefense", () => {
  it("POSTs to /defense", async () => {
    const fake = { alerts: [], triaged: [], hypotheses: [], plan: {} };
    mockPost.mockResolvedValue(fake);

    const result = await cyberApi.blueDefense({ event_stream: [{ type: "scan" }] });
    expect(mockPost).toHaveBeenCalledWith("/defense", { event_stream: [{ type: "scan" }] });
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.getDefense", () => {
  it("GETs /defense/{id}", async () => {
    mockGet.mockResolvedValue({ alerts: [], triaged: [], hypotheses: [], plan: {} });
    await cyberApi.getDefense("range-abc");
    expect(mockGet).toHaveBeenCalledWith("/defense/range-abc");
  });
});

describe("cyberApi.purpleReview", () => {
  it("POSTs to /defense/purple-review", async () => {
    const fake = { critique: {}, review: {} };
    mockPost.mockResolvedValue(fake);

    const body = { attack_chain: { chain_id: "c1" }, response_plan: { plan_id: "p1" }, alerts: [] };
    const result = await cyberApi.purpleReview(body);
    expect(mockPost).toHaveBeenCalledWith("/defense/purple-review", body);
    expect(result).toEqual(fake);
  });
});

describe("cyberApi.getAttackTechniques", () => {
  it("GETs /threat/attack-techniques without tactic filter", async () => {
    mockGet.mockResolvedValue([]);
    await cyberApi.getAttackTechniques();
    expect(mockGet).toHaveBeenCalledWith("/threat/attack-techniques");
  });

  it("appends tactic query param when provided", async () => {
    mockGet.mockResolvedValue([]);
    await cyberApi.getAttackTechniques("Execution");
    expect(mockGet).toHaveBeenCalledWith("/threat/attack-techniques?tactic=Execution");
  });

  it("encodes special characters in tactic", async () => {
    mockGet.mockResolvedValue([]);
    await cyberApi.getAttackTechniques("Initial Access");
    expect(mockGet).toHaveBeenCalledWith("/threat/attack-techniques?tactic=Initial%20Access");
  });
});
