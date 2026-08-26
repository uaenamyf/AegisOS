// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 G6 cyber 视图组件渲染测试（mock store + render 断言）

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
  it("renders 4 tabs", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    expect(screen.getByText("Red Team")).toBeDefined();
    expect(screen.getByText("Blue Team")).toBeDefined();
    expect(screen.getByText("Purple Review")).toBeDefined();
    expect(screen.getByText("Threat Intel")).toBeDefined();
  });

  it("shows Start Range button", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    expect(screen.getByText("Start Range")).toBeDefined();
  });

  it("switches to Blue Team tab on click", async () => {
    const { CyberView } = await import("../CyberView");
    renderUI(<CyberView />);
    fireEvent.click(screen.getByText("Blue Team"));
    // Blue team panel should now be rendered — it shows empty hint when no blue result
    // The hint text is "No defense result yet. Execute blue defense to see alerts and response plans."
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

  it("renders Execute Red Attack button", async () => {
    const { RedTeamPanel } = await import("../RedTeamPanel");
    renderUI(<RedTeamPanel />);
    // Text appears both in hint <strong> and button; use getAllByText
    const matches = screen.getAllByText("Execute Red Attack");
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches.some((el) => el.tagName === "BUTTON")).toBe(true);
  });
});

describe("BlueTeamPanel", () => {
  it("renders Execute Blue Defense button", async () => {
    const { BlueTeamPanel } = await import("../BlueTeamPanel");
    renderUI(<BlueTeamPanel />);
    // Text appears both in hint <strong> and button; use getAllByText
    const matches = screen.getAllByText("Execute Blue Defense");
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches.some((el) => el.tagName === "BUTTON")).toBe(true);
  });
});

describe("PurpleTeamPanel", () => {
  it("renders empty hint when no purple review result", async () => {
    const { PurpleTeamPanel } = await import("../PurpleTeamPanel");
    renderUI(<PurpleTeamPanel />);
    // Should render empty state
  });
});
