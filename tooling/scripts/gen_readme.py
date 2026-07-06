#!/usr/bin/env python3
# date: 2026-07-03
# dev: myf

"""动态生成根目录 README.md 的脚本。

本脚本扫描 AegisOS 仓库的真实结构，统计目录/文件/AGENT.md/API 接口等
指标，并拼装为 Markdown 文档写入仓库根目录的 README.md。

运行方式：
    python3 tooling/scripts/gen_readme.py

每当仓库结构发生变化后重新运行，即可保持 README.md 与实际结构同步。
"""

from __future__ import annotations

import os
from datetime import date

# 仓库根目录：本文件位于 tooling/scripts/，向上回溯三级即为根目录
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 绝不应计入项目内容的目录（虚拟环境、本地工具、缓存、构建产物等）。
# 应用于下方每一次 os.walk，确保统计结果真实可靠。
_EXCLUDE_DIRS = (
    ".git",
    ".venv",
    "venv",
    ".claude",
    "node_modules",
    "__pycache__",
    "aegisos.egg-info",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
)


def _excluded(dp: str) -> bool:
    """判断给定相对路径是否落在排除目录内。

    将路径按斜杠切分后，逐段检查是否命中 ``_EXCLUDE_DIRS``。

    Args:
        dp: 相对于仓库根目录的路径字符串（可含反斜杠）。

    Returns:
        若路径任意一段命中排除目录则返回 True，否则返回 False。
    """
    parts = dp.replace("\\", "/").split("/")
    return any(seg in _EXCLUDE_DIRS for seg in parts)


def count(pattern_dir: str, name: str) -> int:
    """统计指定目录树下某文件名的出现次数。

    在 ``pattern_dir`` 子树中递归遍历，统计名为 ``name`` 的文件数量，
    跳过排除目录。

    Args:
        pattern_dir: 相对于仓库根目录的起始目录。
        name: 需要计数的文件名（如 ``AGENT.md``）。

    Returns:
        命中文件的计数结果。
    """
    n = 0
    for dp, _, files in os.walk(os.path.join(ROOT, pattern_dir)):
        if _excluded(dp):
            continue
        n += files.count(name)
    return n


def list_dir(rel: str, depth: int = 1) -> list[str]:
    """以缩进列表形式列出目录内容，支持多级深度。

    Args:
        rel: 相对于仓库根目录的目录路径。
        depth: 递归深度，默认为 1（仅列出直接子项）。

    Returns:
        目录条目列表；子级条目以两个空格缩进表示层级。若目录不存在
        则返回空列表。
    """
    base = os.path.join(ROOT, rel)
    if not os.path.isdir(base):
        return []
    entries = sorted(os.listdir(base))
    out = []
    for e in entries:
        # 跳过隐藏文件和双下划线目录（如 __pycache__）
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
    """汇总各域的公共 API 接口列表。

    遍历预定义的域列表，定位每个域的 ``api/__init__.py``，解析其中的
    ``__all__`` 声明，提取含 ``API`` 关键字的导出名称。

    Returns:
        元组列表，每项为 ``(域文件夹名, api 模块全名, 接口名列表)``。
    """
    # 各域配置：(文件夹名, api 模块全名, api 子目录)
    domains = [
        ("agents", "agents.api", "api"),
        ("backend", "backend.api", "api"),
        ("frontend", None, None),  # frontend has no Python API (deleted)
        ("infrastructure", "infrastructure.api", "api"),
        ("observability", "observability.api", "api"),
        ("data", "data.api", "api"),
        ("tooling", "tooling.api", "api"),
    ]
    out = []
    for folder, mod, api_sub in domains:
        # 无 Python API 的域直接记为空接口
        if api_sub is None:
            out.append((folder, mod or "", []))
            continue
        api_dir = os.path.join(ROOT, folder, *api_sub.split("/"), "__init__.py")
        names: list[str] = []
        if os.path.isfile(api_dir):
            with open(api_dir, encoding="utf-8") as f:
                src = f.read()
            # 解析 __all__ = [ "X", "Y", ... ] 声明块
            start = src.find("__all__")
            if start != -1:
                bracket = src.find("[", start)
                end = src.find("]", bracket)
                block = src[bracket:end]
                # 提取所有带引号的标识符，仅保留名称中含 API 的项
                import re

                names = [
                    m.strip('"').strip("'")
                    for m in re.findall(r'["\']([\w]+)["\']', block)
                    if "API" in m
                ]
        out.append((folder, mod, names))
    return out


def tree_block() -> str:
    """生成仓库目录树的可视化 Markdown 代码块。

    遍历顶层目录，最多展示三层子目录，每层以两个空格缩进。
    跳过隐藏目录和 ``__pycache__``。

    Returns:
        由 ```` ``` ```` 包裹的目录树字符串。
    """
    lines = ["```"]
    # 第一层：顶层目录
    top = sorted(
        d
        for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d)) and not d.startswith(".")
    )
    for d in top:
        lines.append(f"{d}/")
        # 第二层：顶层目录的直接子目录
        sub = sorted(
            s
            for s in os.listdir(os.path.join(ROOT, d))
            if os.path.isdir(os.path.join(ROOT, d, s))
            and not s.startswith(".")
            and s != "__pycache__"
        )
        for s in sub:
            lines.append(f"  {s}/")
            # 第三层：二级目录的子目录
            ssub = sorted(
                x
                for x in os.listdir(os.path.join(ROOT, d, s))
                if os.path.isdir(os.path.join(ROOT, d, s, x))
                and not x.startswith(".")
                and x != "__pycache__"
            )
            for x in ssub:
                lines.append(f"    {x}/")
    lines.append("```")
    return "\n".join(lines)


def main() -> None:
    """生成并写入根目录 README.md。

    采集仓库统计指标、API 接口摘要与目录树，拼装 Markdown 内容
    后写入 ``README.md``，并在终端打印摘要信息。
    """
    agent_md = count(".", "AGENT.md")
    # 统计 Python 文件数量，跳过排除目录
    py_files = sum(
        1 for dp, _, fs in os.walk(ROOT) if not _excluded(dp) for f in fs if f.endswith(".py")
    )
    # 统计 Markdown 文件数量
    md_files = sum(
        1 for dp, _, fs in os.walk(ROOT) if not _excluded(dp) for f in fs if f.endswith(".md")
    )
    # 目录总数：所有未排除目录减去根目录自身
    total_dirs = sum(1 for dp, _, _ in os.walk(ROOT) if not _excluded(dp)) - 1
    total_files = sum(len(fs) for dp, _, fs in os.walk(ROOT) if not _excluded(dp))
    apis = api_summary()
    total_apis = sum(len(n) for _, _, n in apis)

    # 拼装 API 解耦表
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

## 实际目录结构（自动生成）
{tree_block()}

## 仓库统计（自动生成，{date.today()}）
| 指标 | 数量 |
|------|------|
| 顶层域 | {len([d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and not d.startswith(".") and d not in _EXCLUDE_DIRS])} |
| 总目录 | {total_dirs} |
| 总文件 | {total_files} |
| AGENT.md | {agent_md} |
| Python 文件 | {py_files} |
| Markdown 文件 | {md_files} |
| 公共 API 接口 | {total_apis} |
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
"""

    # 将拼装好的内容写入根目录 README.md
    out = os.path.join(ROOT, "README.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"README.md generated: {out}")
    print(f"  AGENT.md={agent_md}  APIs={total_apis}  dirs={total_dirs}  files={total_files}")


if __name__ == "__main__":
    main()
