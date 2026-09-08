# AegisOS

> **Agent Operating System (AOS) + AI Native IDE** — 面向「挑战杯揭榜挂帅 + 荣耀群体智能赛题」的可由 Agent 自主开发与运行的群体智能系统。

## 核心特性
- **动态异构群体智能**（Dynamic Heterogeneous Topology）
- **长期记忆**（Long-term Memory，含知识库）
- **低熵通信**（Low Entropy Communication，稀疏链式路由）
- **端边云协同**（Edge-Cloud Collaboration）
- **可运行系统**（Runnable System，开箱可部署）
- **AI 可自主开发**（Developer Operating System + 全仓库 AGENT.md 规范体系）

## 架构总览
```
┌──────────────────────────────────────────────────┐
│  frontend/  表现层（Controller-Service-Mapper + Views）│
├──────────────────────────────────────────────────┤
│  backend/   应用层（Controller-Service-Mapper + Gateway）│
├──────────────────────────────────────────────────┤
│  agents/    智能体域（感知-规划-行动-记忆-工具 五层）   │
├──────────────────────────────────────────────────┤
│  protocol/  契约层（唯一数据契约）                    │
├──────────────────────────────────────────────────┤
│  infrastructure/  基础设施层（传输-节点-交付）         │
└──────────────────────────────────────────────────┘
  observability/  可观测与评估（观测-度量-呈现）
  data/  tooling/  docs/  tests/  developer/  支撑与规范
```

## 顶层目录
| 目录 | 角色 | 内部分类 | 公共 API |
|------|------|----------|----------|
| `developer/` | 规范层（项目大脑） | `*.md` + `roadmap/`(P0..P7) | — |
| `protocol/` | 契约层 | 数据类（Message/Event/Task/...） | 本身即全局契约 |
| `frontend/` | 表现层 | controllers · services · mappers · views | `frontend/api/` |
| `backend/` | 应用层 | controllers · services · mappers · gateway | `backend/api/` |
| `agents/` | 智能体域 | perception · planning · action · memory · tools | `agents/api/` |
| `infrastructure/` | 基础设施层 | transport · nodes · delivery | `infrastructure/api/` |
| `observability/` | 可观测与评估层 | inspect · measure · present | `observability/api/` |
| `data/` | 数据层 | datasets · models | `data/api/` |
| `tooling/` | 工程支撑层 | configs · scripts | `tooling/api/` |
| `docs/` | 文档资产层 | api · architecture · guides · assets · examples | — |
| `tests/` | 测试 | unit · integration · e2e · fixtures · benchmarks | — |

### agents/ — 认知架构五层（感知-规划-行动-记忆-工具）
| 分类 | 内容 |
|------|------|
| `agents/perception/` 感知 | context(上下文) · reasoning(推理) · reflection(反思评估) |
| `agents/planning/` 规划 | planner(角色) · orchestrator(角色) · engine/(planner·scheduler·router·workflow·eventbus·topology) |
| `agents/action/` 行动 | coder·executor·tester·debugger·critic·reviewer·researcher·docwriter(角色) + execution/(executor沙箱·tools) |
| `agents/memory/` 记忆 | 12 子模块（含 semantic 知识库） |
| `agents/tools/` 工具 | llms(模型调用) · prompts(提示词) · runtime(运行时) |

### backend/ — Controller-Service-Mapper + Gateway
`gateway/`(入口) -> `controllers/`(参数校验/响应封装) -> `services/`(业务逻辑) -> `mappers/`(数据转换/持久化)

### frontend/ — Controller-Service-Mapper + Views
`controllers/`(交互/事件) -> `services/`(API/实时/状态) -> `mappers/`(数据转换/共享) -> `views/`(canvas·graph·monitor·replay)

## 模块间 API 解耦
每个域通过 `api/` 子包暴露公共接口，其他模块只通过 `from {domain}.api import ...` 调用，不直接访问内部实现。

| 域 | api 包 | 公共接口数 | 接口 |
|----|--------|-----------|------|
| agents/ | `agents.api` | 0 |  |
| backend/ | `backend.api` | 0 |  |
| frontend/ | `` | 0 |  |
| infrastructure/ | `infrastructure.api` | 4 | CommunicationAPI · NodeRegistryAPI · SyncAPI · DeploymentAPI |
| observability/ | `observability.api` | 6 | MonitorAPI · TraceAPI · ReplayAPI · BenchmarkAPI · EvaluationAPI · VisualizationAPI |
| data/ | `data.api` | 4 | DatasetAPI · ModelSchemaAPI · GraphStoreAPI · VectorStoreAPI |
| tooling/ | `tooling.api` | 2 | ConfigAPI · ScriptAPI |

> 共 **16** 个公共接口。接口参数/返回值一律使用 `protocol/` 契约类型。`api/` 签名变更属破坏性变更。

## 数据流
```
User Goal
  -> backend/gateway -> backend/controllers -> backend/services
  -> agents/planning/engine/planner: 分解为 Plan(DAG)
  -> agents/planning/engine/topology: 构建动态异构图
  -> agents/planning/engine/router: 低熵路由选择 Agent 链
  -> agents/planning/engine/scheduler: 调度执行
  -> agents/tools/runtime: 托管 Agent 生命周期
  -> agents/action/{role}: receive->think->tool->reflect->respond
     ├─ agents/memory: 读写 MemoryPacket
     ├─ agents/action/execution/(tools+executor): 执行工具
     ├─ agents/tools/llms: 推理
     └─ agents/perception/reflection: 自评并写入 agents/memory/reflection
  -> agents/planning/engine/eventbus: 广播事件
  -> observability/inspect/(monitor+replay): 观测与记录
  -> observability/measure/evaluation: 评估
  -> frontend: 实时可视化
```

## 通信协议
自研分层协议（非裸 JSON）：`protocol/` 定义 Message 信封 + 强类型 Payload。
- Message: message_id/parent_id/task_id/workflow_id/sender/receiver/priority/ttl/timestamp/payload
- Event: AgentStart/AgentFinish/ToolCall/ToolFinish/Retry/Rollback/MemoryUpdate/GraphUpdate
- 动态路由: Task -> Semantic Graph -> Agent Graph -> Dynamic Routing -> Sparse Communication -> Adaptive Graph -> Graph Update

详见 `developer/specs/04_PROTOCOL_SPEC.md`。

## 开发流程（AI 自主开发）
```
Developer Agent
  -> 读取 developer/specs/（00_PROJECT_SPEC 等）+ roadmap/ 定位阶段
  -> 读取目标模块 AGENT.md（职责/边界/接口）
  -> 读取 protocol/ 契约 + tooling/configs/ 配置
  -> 生成代码 -> 运行 tests/ -> 更新文档与 CHANGELOG -> commit
```
Agent 永不扫描整个项目；按模块边界精准读写。

## 快速开始
```bash
make setup        # 初始化环境
make test         # 运行测试
make build        # 构建产物/镜像
make deploy ENV=dev
```

## CyberDrill 攻防演练演示（无人干预一键跑通）

> 场景 1「网络防御（红→蓝→紫完整链路）」一键闭环，赛事演示主场景。
> 演示脚本**无人干预**全自动完成：启动后端 → 发起演练 → 多轮收敛 → 输出总结与落盘记录。

### 一键演示（推荐）
```powershell
# Windows PowerShell（要求能 import fastapi 的 Python 在 PATH，或设置 $env:AEGIS_PYTHON）
.\tooling\scripts\drill_demo.ps1

# 自定义参数
.\tooling\scripts\drill_demo.ps1 -TargetRange 192.168.1.0/24 -MaxRounds 3
.\tooling\scripts\drill_demo.ps1 -UseRealModel   # 切换真实 LLM（需 OPENAI_API_KEY）
.\tooling\scripts\drill_demo.ps1 -SkipBackendStart # 后端已在运行时跳过自动启动
.\tooling\scripts\drill_demo.ps1 -KeepRunning      # 演示结束不停止自动启动的后端
```

脚本自动完成：探测 Python → 启动 uvicorn（默认 mock 模式）→ `POST /drill/start` →
轮询至收敛 → 打印收敛码/轮数/总结/跨轮记忆轨迹/落盘路径。如终端中文乱码，先执行 `chcp 65001` 或使用 Windows Terminal。

### 手动演示
```powershell
.\start.ps1 backend     # 启动后端（默认 mock；设 AEGIS_USE_MOCK=false + OPENAI_API_KEY 切真实）
# 另开终端:
.\start.ps1 frontend    # 启动前端 → http://localhost:5173 → 侧边栏 Cyber → Drill tab
```

### 能力落点（R1-R11）
| 轮次 | 能力 | 演示可见证据 |
|---|---|---|
| R1-R1.5 | 收敛内核 + mock 按轮演化 | 多轮演练自动收敛（3-5 轮内收敛码 converged） |
| R2 | 演练持久化 | `data/drills/<drill_id>.json` 落盘可回放 |
| R3 | drill 路由 REST+SSE | `/api/v1/drill/*` 5 端点；`/docs` 可调试 |
| R5 | 前端演练视图 | Drill tab 开始/停止 + 轮次时间线 + 总结报告 |
| R7 | 真实 LLM 接入 | 运行时 mock/real 模式切换 + 前端徽标 |
| R8 | 跨轮记忆与上下文压缩 | 轮次卡 🧠 mem 徽标 + 总结「Cross-Round Memory」区 |
| R9 | 事件总线化 | `GET /api/v1/events?stream=drill.round` 订阅增量战报 |
| R10 | 端-边-云自适应调度 | 轮次卡 red/blue/purple 三阶段 tier 徽标 + 卸载理由 |

### 实测指引
| 层 | 怎么测 | 看什么 |
|---|---|---|
| 后端 | 脚本或 `start.ps1 backend` | `/api/v1/health`；`/docs` 调 drill 端点（X-API-Key: aegis-dev-key） |
| 前端 | `start.ps1 frontend` → Cyber | Drill tab 时间线 + 总结 + mem/placement 徽标 |
| 事件流 | 演练进行中 | `GET /api/v1/events?stream=drill.round` |
| 数据落盘 | 演练结束 | `data/drills/<drill_id>.json`（各轮战报 + 总结） |

## 实际目录结构（自动生成）
```
aegisos.egg-info/
aegisos_agents/
  action/
    coder/
    critic/
    debugger/
    detector/
    docwriter/
    execution/
    executor/
    exploit_planner/
    forensics/
    ir_planner/
    lateral_move/
    recon/
    researcher/
    reviewer/
    tester/
    threat_hunt/
    triage/
    vuln_correlator/
  api/
  memory/
    archive/
    cache/
    checkpoint/
    compression/
    episodic/
    recall/
    reflection/
    retrieval/
    semantic/
    snapshot/
    sync/
    vector/
    working/
  perception/
    context/
    reasoning/
    reflection/
  planning/
    engine/
    orchestrator/
    planner/
  tools/
    llms/
    prompts/
    runtime/
backend/
  core/
  mocks/
  models/
  repositories/
  routers/
  schemas/
  services/
data/
  api/
  datasets/
    attck/
  models/
developer/
  specs/
docs/
  examples/
  superpowers/
    plans/
    specs/
frontend/
  node_modules/
    @asamuzakjp/
    @babel/
    @csstools/
    @esbuild/
    @eslint/
    @eslint-community/
    @humanwhocodes/
    @jridgewell/
    @nodelib/
    @playwright/
    @rolldown/
    @rollup/
    @testing-library/
    @types/
    @typescript-eslint/
    @ungap/
    @vitejs/
    @vitest/
    acorn/
    acorn-jsx/
    agent-base/
    ajv/
    ansi-regex/
    ansi-styles/
    argparse/
    aria-query/
    assertion-error/
    asynckit/
    balanced-match/
    baseline-browser-mapping/
    brace-expansion/
    browserslist/
    cac/
    call-bind-apply-helpers/
    callsites/
    caniuse-lite/
    chai/
    chalk/
    check-error/
    color-convert/
    color-name/
    combined-stream/
    concat-map/
    convert-source-map/
    cross-spawn/
    cssstyle/
    csstype/
    data-urls/
    debug/
    decimal.js/
    deep-eql/
    deep-is/
    delayed-stream/
    dequal/
    doctrine/
    dom-accessibility-api/
    dunder-proto/
    electron-to-chromium/
    entities/
    es-define-property/
    es-errors/
    es-module-lexer/
    es-object-atoms/
    es-set-tostringtag/
    esbuild/
    escalade/
    escape-string-regexp/
    eslint/
    eslint-plugin-react-hooks/
    eslint-plugin-react-refresh/
    eslint-scope/
    eslint-visitor-keys/
    espree/
    esquery/
    esrecurse/
    estraverse/
    estree-walker/
    esutils/
    expect-type/
    fast-deep-equal/
    fast-json-stable-stringify/
    fast-levenshtein/
    fastq/
    fdir/
    file-entry-cache/
    find-up/
    flat-cache/
    flatted/
    form-data/
    fs.realpath/
    function-bind/
    gensync/
    get-intrinsic/
    get-proto/
    glob/
    glob-parent/
    globals/
    gopd/
    graphemer/
    has-flag/
    has-symbols/
    has-tostringtag/
    hasown/
    html-encoding-sniffer/
    http-proxy-agent/
    https-proxy-agent/
    iconv-lite/
    ignore/
    import-fresh/
    imurmurhash/
    inflight/
    inherits/
    is-extglob/
    is-glob/
    is-path-inside/
    is-potential-custom-element-name/
    isexe/
    js-tokens/
    js-yaml/
    jsdom/
    jsesc/
    json-buffer/
    json-schema-traverse/
    json-stable-stringify-without-jsonify/
    json5/
    keyv/
    levn/
    locate-path/
    lodash.merge/
    loose-envify/
    loupe/
    lru-cache/
    lz-string/
    magic-string/
    math-intrinsics/
    mime-db/
    mime-types/
    minimatch/
    ms/
    nanoid/
    natural-compare/
    node-releases/
    nwsapi/
    once/
    optionator/
    p-limit/
    p-locate/
    parent-module/
    parse5/
    path-exists/
    path-is-absolute/
    path-key/
    pathe/
    pathval/
    picocolors/
    picomatch/
    playwright/
    playwright-core/
    postcss/
    prelude-ls/
    prettier/
    pretty-format/
    punycode/
    queue-microtask/
    react/
    react-dom/
    react-is/
    react-refresh/
    resolve-from/
    reusify/
    rimraf/
    rollup/
    rrweb-cssom/
    run-parallel/
    safer-buffer/
    saxes/
    scheduler/
    semver/
    shebang-command/
    shebang-regex/
    siginfo/
    source-map-js/
    stackback/
    std-env/
    strip-ansi/
    strip-json-comments/
    supports-color/
    symbol-tree/
    text-table/
    tinybench/
    tinyexec/
    tinyglobby/
    tinypool/
    tinyrainbow/
    tinyspy/
    tldts/
    tldts-core/
    tough-cookie/
    tr46/
    ts-api-utils/
    type-check/
    type-fest/
    typescript/
    undici-types/
    update-browserslist-db/
    uri-js/
    use-sync-external-store/
    vite/
    vite-node/
    vitest/
    w3c-xmlserializer/
    webidl-conversions/
    whatwg-encoding/
    whatwg-mimetype/
    whatwg-url/
    which/
    why-is-node-running/
    word-wrap/
    wrappy/
    ws/
    xml-name-validator/
    xmlchars/
    yallist/
    yocto-queue/
    zustand/
  src/
    config/
    controllers/
    lib/
    protocol/
    services/
    views/
infrastructure/
  api/
  delivery/
    deployment/
  nodes/
    cloud/
    device/
    edge/
  transport/
    communication/
observability/
  api/
  inspect/
    monitor/
    replay/
  measure/
    benchmark/
    evaluation/
  present/
    visualization/
protocol/
tests/
  aegisos_agents/
    action/
    memory/
    perception/
    planning/
    tools/
  backend/
  data/
  e2e/
  observability/
  protocol/
tooling/
  api/
  configs/
  scripts/
```

## 仓库统计（自动生成，2026-08-06）
| 指标 | 数量 |
|------|------|
| 顶层域 | 11 |
| 总目录 | 139 |
| 总文件 | 437 |
| AGENT.md | 83 |
| Python 文件 | 245 |
| Markdown 文件 | 117 |
| 公共 API 接口 | 16 |
| protocol 契约类型 | 26 |

## 关键文档
- `AGENT.md` — 仓库总规范（最高优先级）
- `developer/specs/README.md` — 规范体系索引（SSOT）
- `developer/specs/00_PROJECT_SPEC.md` — 项目 SSOT（目标/边界/生命周期）
- `developer/specs/01_ARCHITECTURE_SPEC.md` — 系统总体架构
- `developer/specs/04_PROTOCOL_SPEC.md` — 通信协议规范
- `developer/specs/02_DIRECTORY_SPEC.md` — 仓库目录导航
- `developer/specs/05_API_SPEC.md` — API 接口规范
- `developer/specs/11_AI_CODING_SPEC.md` — AI 编码规范
- `developer/roadmap/README.md` — 系统级开发计划 P0..P7
- 各目录 `AGENT.md` — 模块边界与开发规范

## 许可
（待定）
