# 智能体任务前必读 · Skills 总览

> **本文件为 `.claude/skills/` 的入口文档。每次接到任务、在动手写代码或调用工具之前，请先通读本文件，判断当前任务是否匹配下方某个 skill，并按需加载其 `SKILL.md`。**
>
> Skills 是「按需渐进加载」的：默认只有 name + description 在上下文中，正文与附带资源仅在被触发时才读入。先看本目录索引、再决定读哪个 SKILL.md，可以避免一次性把大量文档灌进上下文窗口。

---

## 一、为什么要先读这里

- **避免重复造轮子**：多数常见工作流（设计、TDD、调试、建 MCP、写 artifact、测试 web 应用）都有现成 skill 与脚本，直接复用比从零写更可靠。
- **避免上下文污染**：skill 目录里的脚本往往是「黑盒调用」的（如 `webapp-testing` 的 `with_server.py`），应直接 `--help` 调用，而不是把源码读进上下文。
- **方法论一致性**：`superpowers` 套件提供了一套完整的软件开发方法论（头脑风暴 → 计划 → TDD 实现 → 审查 → 收尾），遵循它能让多智能体协作更可控。

**判断流程**：任务到手 → 扫一眼下表 → 命中则点开对应 `SKILL.md` → 未命中再自行处理。

---

## 二、Skills 清单

### A. 前端 / 设计类

#### 1. frontend-design — 前端视觉设计指导
- **作用**：以「小型设计工作室主理人」的视角，给出有辨识度、非模板化的视觉方案（配色、字体配对、版式、动效、文案）。
- **适用场景**：新建 UI 或重塑现有界面、需要做审美方向决策、不想产出「AI 味」的默认设计时。
- **文档**：[`frontend-design/SKILL.md`](./frontend-design/SKILL.md)

#### 2. web-artifacts-builder — claude.ai HTML Artifact 构建
- **作用**：用脚本初始化 React + TS + Vite + Tailwind + shadcn/ui 工程，开发完成后打包成单一自包含 `bundle.html`，可直接作为 artifact 分享。
- **适用场景**：需要构建复杂、多组件、含状态管理 / 路由 / shadcn 组件的 artifact；**不**适用于简单的单文件 HTML/JSX。
- **配套脚本**：`init-artifact.sh`（建工程）、`bundle-artifact.sh`（打包）。
- **文档**：[`web-artifacts-builder/SKILL.md`](./web-artifacts-builder/SKILL.md)

---

### B. 工具 / 集成类

#### 3. mcp-builder — MCP Server 开发指南
- **作用**：指导构建高质量的 MCP（Model Context Protocol）服务器，让 LLM 通过工具与外部服务交互。覆盖研究、实现、审查测试、评估四阶段。
- **适用场景**：要为外部 API / 服务构建 MCP 集成时（推荐 TypeScript + Streamable HTTP，也支持 Python/FastMCP）。
- **附带资源**：`reference/` 下有 best practices、Python/TS 实现指南、评估指南。
- **文档**：[`mcp-builder/SKILL.md`](./mcp-builder/SKILL.md)

#### 4. codex-plugin-cc-main — 在 Claude Code 中调用 Codex（插件）
- **作用**：把任务委派给 Codex，或用 Codex 做代码审查。提供一组斜杠命令与后台任务管理。
- **核心命令**：
  - `/codex:review` — 普通只读代码审查
  - `/codex:adversarial-review` — 可引导的对抗式审查（质疑设计 / 假设 / 风险点）
  - `/codex:rescue` — 把调查 bug / 尝试修复等任务交给 Codex
  - `/codex:transfer` — 把当前会话上下文转为 Codex 持久线程
  - `/codex:status` / `/codex:result` / `/codex:cancel` — 管理后台任务
  - `/codex:setup` — 检查 Codex 是否就绪
- **前置条件**：ChatGPT 订阅或 OpenAI API key + Node.js 18.18+。
- **文档**：[`codex-plugin-cc-main/README.md`](./codex-plugin-cc-main/README.md)（命令细节见 `plugins/codex/commands/`）

---

### C. Skill 元工具类

#### 5. skill-creator — 创建 / 改进 / 评估 skill
- **作用**：从零创建新 skill、迭代改进已有 skill，并通过定量 benchmark + 可视化评审器衡量其表现，还能优化 description 以提升触发准确率。
- **适用场景**：用户想新建 skill、编辑现有 skill、跑 eval 测试 skill、做方差分析基准、优化 skill 的触发描述时。
- **附带资源**：`agents/`（grader / comparator / analyzer 子智能体）、`eval-viewer/`、`references/schemas.md`。
- **文档**：[`skill-creator/SKILL.md`](./skill-creator/SKILL.md)

---

### D. 测试类

#### 6. webapp-testing — 本地 Web 应用测试（Playwright）
- **作用**：用原生 Python Playwright 脚本与本地 Web 应用交互，验证前端功能、调试 UI、截图、查看浏览器日志。
- **配套脚本**：`scripts/with_server.py`（管理多服务器生命周期，**先 `--help` 再用**，勿读源码）。
- **关键原则**：动态应用必须先 `page.wait_for_load_state('networkidle')` 再检查 DOM；优先用黑盒脚本而非自写。
- **文档**：[`webapp-testing/SKILL.md`](./webapp-testing/SKILL.md)（示例见 `examples/`）

---

### E. Superpowers 方法论套件（14 个子 skill）

`superpowers-main` 是一套完整的软件开发方法论，**技能会自动触发**。核心工作流：头脑风暴 → 设计 → git worktree 隔离 → 写计划 → 子智能体驱动开发 / TDD → 代码审查 → 收尾分支。总览见 [`superpowers-main/README.md`](./superpowers-main/README.md)。

#### 协作 / 流程类
| 子 Skill | 作用 | 适用场景 | 文档 |
|---|---|---|---|
| **using-superpowers** | 介绍 skills 系统，要求任何响应前先查 skill | 每次会话开始时 | [`SKILL.md`](./superpowers-main/skills/using-superpowers/SKILL.md) |
| **brainstorming** | 苏格拉底式设计精炼，先澄清意图再实现 | 任何创造性工作（建功能 / 组件 / 改行为）之前 | [`SKILL.md`](./superpowers-main/skills/brainstorming/SKILL.md) |
| **writing-plans** | 把需求拆成 2–5 分钟、含确切文件路径与验证步骤的小任务 | 有 spec、动代码之前 | [`SKILL.md`](./superpowers-main/skills/writing-plans/SKILL.md) |
| **executing-plans** | 带人工检查点地分批执行已写好的计划 | 另起会话执行计划时 | [`SKILL.md`](./superpowers-main/skills/executing-plans/SKILL.md) |
| **subagent-driven-development** | 当前会话内用子智能体迭代执行 + 两阶段审查（规格 / 质量） | 计划含可并行的独立任务时 | [`SKILL.md`](./superpowers-main/skills/subagent-driven-development/SKILL.md) |
| **dispatching-parallel-agents** | 并发派发多个子智能体 | 面对 2+ 个无共享状态、无顺序依赖的任务时 | [`SKILL.md`](./superpowers-main/skills/dispatching-parallel-agents/SKILL.md) |
| **using-git-worktrees** | 用原生工具或 git worktree 建隔离工作区 | 开始需要隔离的功能开发 / 执行计划前 | [`SKILL.md`](./superpowers-main/skills/using-git-worktrees/SKILL.md) |
| **finishing-a-development-branch** | 完成后给出 merge / PR / 保留 / 丢弃选项并清理 | 实现完成、测试通过、准备集成时 | [`SKILL.md`](./superpowers-main/skills/finishing-a-development-branch/SKILL.md) |

#### 审查类
| 子 Skill | 作用 | 适用场景 | 文档 |
|---|---|---|---|
| **requesting-code-review** | 提交前的预审查清单，对照计划核验 | 完成任务 / 重大功能 / 合并前 | [`SKILL.md`](./superpowers-main/skills/requesting-code-review/SKILL.md) |
| **receiving-code-review** | 接收审查反馈时保持技术严谨、先验证再实现 | 收到 review 反馈、尤其反馈不清或存疑时 | [`SKILL.md`](./superpowers-main/skills/receiving-code-review/SKILL.md) |

#### 测试 / 调试 / 验证类
| 子 Skill | 作用 | 适用场景 | 文档 |
|---|---|---|---|
| **test-driven-development** | RED-GREEN-REFACTOR：先写失败测试再写实现 | 实现任何功能或修复前 | [`SKILL.md`](./superpowers-main/skills/test-driven-development/SKILL.md) |
| **systematic-debugging** | 4 阶段根因定位流程（含根因追踪 / 纵深防御 / 条件等待） | 遇到 bug / 测试失败 / 异常行为、提方案前 | [`SKILL.md`](./superpowers-main/skills/systematic-debugging/SKILL.md) |
| **verification-before-completion** | 声称「完成 / 修复 / 通过」前必须跑验证命令并确认输出 | 即将宣称完成、提交或建 PR 前 | [`SKILL.md`](./superpowers-main/skills/verification-before-completion/SKILL.md) |

#### 元类
| 子 Skill | 作用 | 适用场景 | 文档 |
|---|---|---|---|
| **writing-skills** | 按最佳实践创建 / 编辑 / 验证 skill | 新建 skill、改 skill、部署前验证时 | [`SKILL.md`](./superpowers-main/skills/writing-skills/SKILL.md) |

> 注：`skill-creator` 与 superpowers 的 `writing-skills` 功能重叠，前者更偏「带 eval/benchmark 的量化迭代」，后者更偏「方法论最佳实践」。按团队偏好选用。

---

## 三、快速决策表

| 任务关键词 | 首选 Skill |
|---|---|
| 做界面 / 配色 / 字体 / 视觉方向 | [`frontend-design`](./frontend-design/SKILL.md) |
| 构建 claude.ai artifact（React/shadcn） | [`web-artifacts-builder`](./web-artifacts-builder/SKILL.md) |
| 给外部 API 做 MCP 集成 | [`mcp-builder`](./mcp-builder/SKILL.md) |
| 委派任务给 Codex / Codex 审查 | [`codex-plugin`](./codex-plugin-cc-main/README.md) |
| 新建 / 改进 / 评估一个 skill | [`skill-creator`](./skill-creator/SKILL.md) |
| 跑 Playwright 测本地 web 应用 | [`webapp-testing`](./webapp-testing/SKILL.md) |
| 动代码前先想清楚要做什么 | [`brainstorming`](./superpowers-main/skills/brainstorming/SKILL.md) |
| 把需求拆成可执行小任务 | [`writing-plans`](./superpowers-main/skills/writing-plans/SKILL.md) |
| 实现功能 / 修 bug | [`test-driven-development`](./superpowers-main/skills/test-driven-development/SKILL.md) |
| 排查 bug / 测试失败 | [`systematic-debugging`](./superpowers-main/skills/systematic-debugging/SKILL.md) |
| 准备提交 / 声称完成前 | [`verification-before-completion`](./superpowers-main/skills/verification-before-completion/SKILL.md) |
| 多任务可并行 | [`dispatching-parallel-agents`](./superpowers-main/skills/dispatching-parallel-agents/SKILL.md) |

---

## 四、使用约定

1. **先索引，后正文**：先读本文件定位 skill，再点开对应 `SKILL.md`，避免无差别读入大文件。
2. **脚本黑盒调用**：`webapp-testing`、`mcp-builder`、`skill-creator` 等目录下的 `scripts/` 应直接 `--help` 调用，不要把源码读进上下文。
3. **链接为相对静态链接**：本文件中所有链接均指向同仓库内的 `SKILL.md` / `README.md`，迁移目录时需同步更新。
4. **新增 skill 后**：请在本文件「Skills 清单」与「快速决策表」补一行，保持索引完整。
5. **若要让智能体真正每次必读**：建议在项目根 `CLAUDE.md` 中加一行指向本文件（如 `执行任务前先阅读 .claude/skills/README.md`），因为 `CLAUDE.md` 会在每次会话自动加载。
