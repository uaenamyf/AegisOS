import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

const state = {
  currentSession: null,
  events: [],
  chatMessages: [],
  tasks: [
    { task_id: "recon", goal: "侦察目标", status: "succeeded", priority: 3, dependency: [] },
    { task_id: "correlate", goal: "关联漏洞", status: "running", priority: 2, dependency: ["recon"] },
    { task_id: "review", goal: "审查结果", status: "pending", priority: 1, dependency: ["correlate"] },
  ] as Array<Record<string, any>>,
  setTasks: vi.fn(),
};

vi.mock("@/lib/store", () => ({
  useAppStore: (selector: (value: typeof state) => unknown) => selector(state),
}));

describe("CanvasView", () => {
  it("renders tasks in dependency stages", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    const stageLabels = screen.getAllByText((_, element) => element?.classList.contains("canvas-column__label") ?? false);
    expect(stageLabels.map((element) => element.textContent?.trim())).toEqual(
      expect.arrayContaining(["阶段 1", "阶段 2", "阶段 3"]),
    );
    expect(screen.getAllByText("侦察目标").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("审查结果").length).toBeGreaterThanOrEqual(1);
  });

  it("filters tasks by status", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    fireEvent.click(screen.getByRole("button", { name: "执行中" }));
    expect(screen.getByText("1 个任务")).toBeDefined();
    expect(screen.getAllByText("关联漏洞").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("侦察目标")).toBeNull();
  });

  it("shows selected task details after clicking a node", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    fireEvent.click(screen.getByRole("button", { name: /审查结果/ }));
    expect(screen.getByRole("complementary", { name: "任务详情" })).toBeDefined();
    expect(screen.getByText("correlate")).toBeDefined();
  });

  it("shows the selected task agent and persisted output", async () => {
    const { CanvasView } = await import("../CanvasView");
    state.tasks = [{
      task_id: "task-with-output",
      goal: "分析暴露面",
      payload: { stage: 1, agent_id: "recon" },
      result: { assets: [{ host: "10.0.0.8" }] },
      status: "succeeded",
      dependency: [],
      priority: 1,
    }];

    render(<CanvasView />);

    expect(screen.getByText(/红队 · 已完成 · recon/)).toBeDefined();
    expect(screen.getByText('{"assets":[{"host":"10.0.0.8"}]}')).toBeDefined();
  });

  it("loads a complete demo flow from the empty state", async () => {
    const { CanvasView } = await import("../CanvasView");
    state.tasks.length = 0;
    render(<CanvasView />);
    expect(screen.getByRole("button", { name: "创建后端攻防流程" })).toBeDefined();
  });
});
