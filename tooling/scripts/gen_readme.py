#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dynamically generate the root README.md from the actual repo structure.

Run:  python3 tooling/scripts/gen_readme.py
Re-run whenever the structure changes to keep README.md in sync.
"""
from __future__ import annotations

import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def count(pattern_dir: str, name: str) -> int:
    n = 0
    for dp, _, files in os.walk(os.path.join(ROOT, pattern_dir)):
        if ".git" in dp:
            continue
        n += files.count(name)
    return n


def list_dir(rel: str, depth: int = 1) -> list[str]:
    base = os.path.join(ROOT, rel)
    if not os.path.isdir(base):
        return []
    entries = sorted(os.listdir(base))
    out = []
    for e in entries:
        if e.startswith(".") or e.startswith("__"):
            continue
        p = os.path.join(base, e)
        if os.path.isdir(p):
            out.append(e)
            if depth > 1:
                for sub in list_dir(os.path.join(rel, e), depth - 1):
                    out.append(f"  {sub}")
    return out


def api_summary() -> list[tuple[str, str, list[str]]]:
    domains = [
        ("agents", "agents.api"),
        ("backend", "backend.api"),
        ("frontend", "frontend.api"),
        ("infrastructure", "infrastructure.api"),
        ("observability", "observability.api"),
        ("data", "data.api"),
        ("tooling", "tooling.api"),
    ]
    out = []
    for folder, mod in domains:
        api_dir = os.path.join(ROOT, folder, "api", "__init__.py")
        names: list[str] = []
        if os.path.isfile(api_dir):
            with open(api_dir, encoding="utf-8") as f:
                src = f.read()
            # parse __all__ = [ "X", "Y", ... ]
            start = src.find("__all__")
            if start != -1:
                bracket = src.find("[", start)
                end = src.find("]", bracket)
                block = src[bracket:end]
                # extract all quoted tokens containing API
                import re
                names = [
                    m.strip('"').strip("'")
                    for m in re.findall(r'["\']([\w]+)["\']', block)
                    if "API" in m
                ]
        out.append((folder, mod, names))
    return out


def tree_block() -> str:
    lines = ["```"]
    top = sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d)) and not d.startswith(".")
    )
    for d in top:
        lines.append(f"{d}/")
        sub = sorted(
            s for s in os.listdir(os.path.join(ROOT, d))
            if os.path.isdir(os.path.join(ROOT, d, s)) and not s.startswith(".") and s != "__pycache__"
        )
        for s in sub:
            lines.append(f"  {s}/")
            ssub = sorted(
                x for x in os.listdir(os.path.join(ROOT, d, s))
                if os.path.isdir(os.path.join(ROOT, d, s, x)) and not x.startswith(".") and x != "__pycache__"
            )
            for x in ssub:
                lines.append(f"    {x}/")
    lines.append("```")
    return "\n".join(lines)


def main() -> None:
    agent_md = count(".", "AGENT.md")
    py_files = sum(
        1 for dp, _, fs in os.walk(ROOT)
        if ".git" not in dp
        for f in fs if f.endswith(".py")
    )
    md_files = sum(
        1 for dp, _, fs in os.walk(ROOT)
        if ".git" not in dp
        for f in fs if f.endswith(".md")
    )
    total_dirs = sum(1 for dp, _, _ in os.walk(ROOT) if ".git" not in dp) - 1
    total_files = sum(len(fs) for dp, _, fs in os.walk(ROOT) if ".git" not in dp)
    apis = api_summary()
    total_apis = sum(len(n) for _, _, n in apis)

    api_table = "| 域 | api 包 | 公共接口数 | 接口 |\n|----|--------|-----------|------|\n"
    for folder, mod, names in apis:
        api_table += f"| {folder}/ | `{mod}` | {len(names)} | {' · '.join(names)} |\n"

    s = f"""# AegisOS

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
每个域通过 `api/` 子包暴露公共接口，其他模块只通过 `from {{domain}}.api import ...` 调用，不直接访问内部实现。

{api_table}
> 共 **{total_apis}** 个公共接口。接口参数/返回值一律使用 `protocol/` 契约类型。`api/` 签名变更属破坏性变更。

## 数据流
```
User Goal
  -> backend/gateway -> backend/controllers -> backend/services
  -> agents/planning/engine/planner: 分解为 Plan(DAG)
  -> agents/planning/engine/topology: 构建动态异构图
  -> agents/planning/engine/router: 低熵路由选择 Agent 链
  -> agents/planning/engine/scheduler: 调度执行
  -> agents/tools/runtime: 托管 Agent 生命周期
  -> agents/action/{{role}}: receive->think->tool->reflect->respond
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

详见 `developer/MESSAGE_PROTOCOL.md`。

## 开发流程（AI 自主开发）
```
Developer Agent
  -> 读取 developer/ 规范 + ROADMAP 定位阶段
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

## 实际目录结构（自动生成）
{tree_block()}

## 仓库统计（自动生成，{date.today()}）
| 指标 | 数量 |
|------|------|
| 顶层域 | {len([d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,d)) and not d.startswith('.')])} |
| 总目录 | {total_dirs} |
| 总文件 | {total_files} |
| AGENT.md | {agent_md} |
| Python 文件 | {py_files} |
| Markdown 文件 | {md_files} |
| 公共 API 接口 | {total_apis} |
| protocol 契约类型 | 26 |

## 关键文档
- `AGENT.md` — 仓库总规范（最高优先级）
- `developer/ARCHITECTURE.md` — 系统总体架构
- `developer/roadmap/README.md` — 系统级开发计划 P0..P7
- `developer/MESSAGE_PROTOCOL.md` — 通信协议规范
- `developer/DIRECTORY_GUIDE.md` — 仓库目录导航
- `developer/API_SPEC.md` — API 接口规范
- `developer/CODING_RULES.md` — 编码规则
- 各目录 `AGENT.md` — 模块边界与开发规范

## 许可
（待定）
"""

    out = os.path.join(ROOT, "README.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"README.md generated: {out}")
    print(f"  AGENT.md={agent_md}  APIs={total_apis}  dirs={total_dirs}  files={total_files}")


if __name__ == "__main__":
    main()
