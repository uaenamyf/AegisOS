import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

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

const baseTasks = state.tasks;

vi.mock("@/lib/store", () => ({
  useAppStore: (selector: (value: typeof state) => unknown) => selector(state),
}));

describe("CanvasView", () => {
  beforeEach(() => {
    state.tasks = baseTasks;
    state.events = [];
    state.chatMessages = [];
  });

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
    expect(within(screen.getByLabelText("任务依赖图")).getByRole("button", { name: /关联漏洞 红队/ })).toBeDefined();
  });

  it("shows selected task details after clicking a node", async () => {
    const { CanvasView } = await import("../CanvasView");
    render(<CanvasView />);

    expect(screen.queryByRole("dialog", { name: "任务详情" })).toBeNull();
    fireEvent.click(screen.getAllByRole("button", { name: /审查结果/ }).at(-1)!);
    expect(screen.getByRole("dialog", { name: "任务详情" })).toBeDefined();
    expect(screen.getByText("correlate")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "关闭任务详情" }));
    expect(screen.queryByRole("dialog", { name: "任务详情" })).toBeNull();
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

    fireEvent.click(within(screen.getByLabelText("任务依赖图")).getByRole("button", { name: /分析暴露面/ }));
    expect(screen.getByText(/红队 · 已完成 · recon/)).toBeDefined();
    const outputPanel = screen.getByText("结构化产出").closest<HTMLElement>(".canvas-output-panel");
    expect(outputPanel).not.toBeNull();
    expect(within(outputPanel!).getByText("assets")).toBeDefined();
    expect(outputPanel?.textContent).toContain("10.0.0.8");
  });

  it("loads a complete demo flow from the empty state", async () => {
    const { CanvasView } = await import("../CanvasView");
    state.tasks = [];
    render(<CanvasView />);
    expect(screen.getByRole("button", { name: "创建后端攻防流程" })).toBeDefined();
  });
});
