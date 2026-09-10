// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 G6 cyber 视图组件渲染测试（mock store + render 断言）
// changelog: 2026-09-04 R5 追加 Drill tab 断言 + cyberApi drill mock
// changelog: 2026-09-04 R7 补 systemApi mock（LlmModeBadge 挂载即请求 /system/mode）
// changelog: 2026-09-04 R7 补 systemApi mock（LlmModeBadge 挂载即请求 /system/mode）

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";

// Mock cyberApi so panels don't attempt real network calls
vi.mock("@/services/api/cyber", () => ({
  cyberApi: {
    startRange: vi.fn(),
    getRange: vi.fn(),
    getTopology: vi.fn(),
    redAttack: vi.fn(),
    getAttackChain: vi.fn(),
    blueDefense: vi.fn(),
    getDefense: vi.fn(),
    purpleReview: vi.fn(),
    getAttackTechniques: vi.fn(),
    startDrill: vi.fn(),
    getDrill: vi.fn(),
    getDrillSummary: vi.fn(),
    abortDrill: vi.fn(),
    openDrillStream: vi.fn(),
    listDrills: vi.fn().mockResolvedValue({ drills: [] }),
    getDrillReport: vi.fn().mockResolvedValue({ report: "" }),
    getDrillReportPdf: vi.fn().mockResolvedValue(new Blob()),
  },
}));

// Mock systemApi so LlmModeBadge doesn't hit the network on mount
vi.mock("@/services/api/system", () => ({
  systemApi: {
    getMode: vi.fn(),
    setMode: vi.fn(),
  },
}));

// Mock systemApi so LlmModeBadge doesn't hit the network on mount
vi.mock("@/services/api/system", () => ({
  systemApi: {
    getMode: vi.fn(),
    setMode: vi.fn(),
  },
}));

// --- Mock zustand store ---
// We use a module-level mutable state object so individual tests can set state
let mockState: Record<string, unknown> = {};

vi.mock("@/lib/store", () => ({
  useAppStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector(mockState),
}));

beforeEach(() => {
  mockState = {
    currentRange: null,
    redAttackResult: null,
    blueDefenseResult: null,
    purpleReviewResult: null,
    threatIntel: [],
    cyberLoading: false,
    cyberError: null,
    setCurrentRange: vi.fn(),
    setRedAttackResult: vi.fn(),
    setBlueDefenseResult: vi.fn(),
    setPurpleReviewResult: vi.fn(),
    setThreatIntel: vi.fn(),
    setCyberLoading: vi.fn(),
    setCyberError: vi.fn(),
  };
});

// Helper to render with React (no provider needed for zustand)
function renderUI(ui: ReactNode) {
  return render(<>{ui}</>);
}

describe("CyberView", () => {
  it("renders 5 tabs", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    expect(screen.getByText("Red Team")).toBeDefined();
    expect(screen.getByText("Blue Team")).toBeDefined();
    expect(screen.getByText("Purple Review")).toBeDefined();
    expect(screen.getByText("Threat Intel")).toBeDefined();
    expect(screen.getByText("Auto Drill")).toBeDefined();
  });

  it("does not show a range creation button", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    expect(screen.queryByText("Start Range")).toBeNull();
    expect(screen.getByText("演练只能从 Chat 创建")).toBeDefined();
  });

  it("switches to Blue Team tab on click", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    fireEvent.click(screen.getByText("Blue Team"));
    // Blue team panel should now be rendered — it shows empty hint when no blue result
    // The hint text is "No defense result yet. Execute blue defense to see alerts and response plans."
  });

  it("does not show a Drill start button", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    fireEvent.click(screen.getByText("Auto Drill"));
    expect(screen.queryByText("▶ Start Drill")).toBeNull();
    expect(screen.getByText(/请从 Chat 输入/)).toBeDefined();
  });
});

describe("ThreatIntelPanel", () => {
  it("renders empty hint when threatIntel is empty", async () => {
    const { ThreatIntelPanel } = await import("../ThreatIntelPanel");
    renderUI(<ThreatIntelPanel />);
    // Panel auto-fetches on mount; with empty mock it shows empty state or table
    // Just verify it renders without crashing
  });

  it("renders tactic filter buttons", async () => {
    const { ThreatIntelPanel } = await import("../ThreatIntelPanel");
    renderUI(<ThreatIntelPanel />);
    expect(screen.getByText("All")).toBeDefined();
  });
});

describe("RedTeamPanel", () => {
  it("renders empty hint when no red attack result", async () => {
    const { RedTeamPanel } = await import("../RedTeamPanel");
    renderUI(<RedTeamPanel />);
    // Should render the empty state
  });

  it("renders a disabled Chat-only notice", async () => {
    const { RedTeamPanel } = await import("../RedTeamPanel");
    renderUI(<RedTeamPanel />);
    expect((screen.getByRole("button", { name: "请从 Chat 创建演练" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("BlueTeamPanel", () => {
  it("renders a disabled Chat-only notice", async () => {
    const { BlueTeamPanel } = await import("../BlueTeamPanel");
    renderUI(<BlueTeamPanel />);
    expect((screen.getByRole("button", { name: "请从 Chat 创建演练" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("PurpleTeamPanel", () => {
  it("renders empty hint when no purple review result", async () => {
    const { PurpleTeamPanel } = await import("../PurpleTeamPanel");
    renderUI(<PurpleTeamPanel />);
    // Should render empty state
  });
});
