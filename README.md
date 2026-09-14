# AegisOS

AegisOS 是面向荣耀 XH-202631 赛题的动态异构群体智能协同推理系统，聚焦超长程复杂任务中的：

- 动态异构 Agent 协同
- 长期记忆与跨轮上下文保持
- Top-K 稀疏通信与动态路由
- 端-边-云任务调度与故障降级
- 红队攻击链、蓝队防御链、紫队一致性审查
- Chat → Drill → TaskMap → Monitor → Replay 的可解释演示闭环

> 安全边界：所有攻防演练默认限定在本地安全演示靶场或 Mock 数据中，不对公网和真实生产系统执行攻击。

## 1. 系统能力

```text
用户自然语言目标
    ↓
Chat 意图识别与安全槽位校验
    ↓
Goal / Plan / ReAct 任务分解
    ↓
动态异构 Top-K 路由
    ↓
红队 Recon → Vuln → Exploit → Lateral
    ↓
蓝队 Detect → Triage → Hunt → IR → Forensics
    ↓
紫队 Critic / Reviewer 一致性审查
    ↓
Memory 写入、压缩、召回、Checkpoint、Snapshot
    ↓
TaskMap / Monitor / Replay / Report
```

系统包含 11 个攻防 Agent：

- 红队：`recon`、`vuln_correlator`、`exploit_planner`、`lateral_move`
- 蓝队：`detector`、`triage`、`threat_hunt`、`ir_planner`、`forensics`
- 紫队：`critic`、`reviewer`

## 2. 快速启动

### Windows 本地启动

推荐使用根目录的一键启动脚本：

```powershell
.\start.ps1
```

默认地址：

```text
前端：http://localhost:5173
后端：http://localhost:8000
API 文档：http://localhost:8000/docs
健康检查：http://localhost:8000/api/v1/health
```

常用命令：

```powershell
.\start.ps1 status
.\start.ps1 restart
.\start.ps1 stop
```

启动器会自动读取根目录 `.env`、探测 Python、启动 FastAPI 和 Vite、同步后端 API Key、等待健康检查并管理进程 PID。

### Linux / macOS

```bash
./start.sh
```

## 3. 配置运行模式

### Mock 演示模式

适合比赛现场完整演示，结果稳定、可重复、无需外部模型服务：

```env
AEGIS_USE_MOCK=true
```

### 真实 ARK 模式

项目支持 OpenAI 兼容协议。将配置写入本机根目录 `.env`，不要提交该文件：

```env
AEGIS_USE_MOCK=false
OPENAI_API_KEY=your-ark-key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
OPENAI_DEFAULT_MODEL=ark-code-latest
AEGIS_AUTH_DEFAULT_KEY=aegis-local-demo-key-2026
```

真实模式经过 `ChatService → ExecutionDispatcher → 动态路由 → ARK` 链路，返回真实的执行层级、节点、模型和延迟。

## 4. 比赛演示流程

启动服务后打开：

```text
http://localhost:5173
```

在 Chat 输入：

```text
请模拟一次完整红蓝紫攻防演练，只在安全演示靶场 10.0.0.0/24 内执行，完成 5 轮
```

推荐演示链路：

```text
Chat
→ 意图识别与安全确认
→ 红蓝紫多轮 Drill
→ TaskMap 查看阶段任务
→ Monitor 查看端边云落点
→ Graph 查看协作拓扑
→ Replay 查看事件与攻防证据
→ Drill History 查看报告
```

攻防只能从 Chat 创建；其他 Cyber 页面用于查看当前演练、停止任务、查看轮次和报告。

## 5. API 入口

后端默认前缀为 `/api/v1`，除健康检查外使用 `X-API-Key` 鉴权。

核心接口：

```text
GET  /api/v1/health
POST /api/v1/chat
POST /api/v1/drill/start
GET  /api/v1/drill/{drill_id}
GET  /api/v1/drill/{drill_id}/stream
POST /api/v1/drill/{drill_id}/abort
GET  /api/v1/graph
GET  /api/v1/replay/{session_id}
GET  /api/v1/memory/{session_id}
GET  /api/v1/infra/nodes
```

## 6. 测试与评测

### Python 全量测试

```powershell
$env:AEGIS_USE_MOCK="true"
$env:AEGIS_AUTH_DEFAULT_KEY="aegis-dev-key"
python -m pytest -q
```

当前基线：

```text
703 passed
```

### 前端测试、构建和 lint

```powershell
Push-Location frontend
npm test -- --run
npm run build
npm run lint
Pop-Location
```

当前基线：

```text
50 passed
Vite build passed
ESLint passed
```

### 比赛确定性证据

```powershell
python tooling/scripts/run_competition_eval.py --output docs/XH-202631-engineering-evidence.md
```

评测覆盖 5/10/20 轮长程任务、目标保持、红蓝事件同源、记忆隔离、Checkpoint 恢复、端边云调度和节点失效降级。

### 低熵通信检查

```powershell
python tooling/scripts/check_no_broadcast.py --strict
```

## 7. 比赛报告

综合报告：

[docs/XH-202631-competition-evaluation-report.md](docs/XH-202631-competition-evaluation-report.md)

确定性工程证据：

[docs/XH-202631-engineering-evidence.md](docs/XH-202631-engineering-evidence.md)

方案原文：

`XH-202631荣耀终端股份有限公司-面向超长程复杂任务的动态异构群体智能架构与深度协同推理技术比赛方案.pdf`

真实 ARK 已完成：

- Chat 真实请求 3/3 成功
- 真实单轮 Drill 完成
- 真实两轮 Drill 完成
- 结构化输出重试修复后真实三轮 Drill 完成

## 8. 真实 API 评估

后端启动并配置真实 ARK 后执行：

```powershell
$env:AEGIS_AUTH_DEFAULT_KEY="aegis-local-demo-key-2026"
python tooling/scripts/run_real_api_eval.py
```

评估覆盖健康检查、运行模式、端边云节点、普通 Chat、系统状态 Chat、攻防意图安全拦截、记忆、Graph 和 Drill 历史，共 9 个真实 API 用例。

## 9. 当前限制

以下内容已实现算法、Mock 验收或接口基础，但仍需要现场环境实测：

- 真实 5/10/20 轮 ARK 性能样本
- 真实 device/edge/cloud 网络节点联调
- Neo4j/Qdrant 在线服务集成
- 生产级 HTTPS、Secret 管理和 ASGI 部署

这些限制已经在比赛综合测评报告中明确列出，Mock 结果不会被表述为真实生产性能。

## 10. 目录说明

```text
aegisos_agents/    感知、规划、行动、记忆、工具五层智能体域
backend/            FastAPI、任务、Chat、Drill、Memory、Graph、Replay
frontend/           Chat、TaskMap、Monitor、Graph、Replay、Cyber 视图
protocol/           Message、Event、Task、Memory、Cyber 等唯一契约
infrastructure/    节点注册、端边云派发和通信
observability/      Monitor、Replay、Benchmark、Evaluation、Visualization
data/               ATT&CK 数据、图存储、向量存储
tooling/             配置、启动、部署和比赛评测脚本
tests/               单元、集成、E2E、benchmark 测试
docs/                架构、评测报告和比赛材料
developer/           项目规范、计划和路线图
```
