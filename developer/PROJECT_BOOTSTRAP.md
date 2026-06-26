# PROJECT_BOOTSTRAP.md — 项目引导

> 让 AegisOS 开箱即可开始开发。

## 环境要求
- Python 3.11+、Node 20+、Docker、Make。
- 工具：ruff、mypy、pytest、pytest-asyncio、pytest-cov。

## 初始化
```bash
make setup        # tooling/scripts/setup/ 安装依赖与 pre-commit
make test         # 运行测试
make build        # 构建产物/镜像
make deploy ENV=dev
```

## 目录模板
每个新模块应包含：
- `AGENT.md`（10 项字段：职责/读取目录/禁止修改目录/输出/依赖/接口/测试方式/日志位置/Prompt 位置/配置位置）
- `__init__.py`（Python 子系统）
- 对应 `tests/{module}/`

## 配置模板
- `tooling/configs/environments/{dev,staging,prod}.yaml`
- `tooling/configs/{module}.yaml`、`tooling/configs/agents/{agent}.yaml`、`tooling/configs/data/models/`、`tooling/configs/agents/tools/prompts/`

## CI/CD
- `infrastructure/delivery/deployment/ci/`：lint -> typecheck -> test -> build -> deploy。
- PR 必须通过全部检查。

## Docker
- `infrastructure/delivery/deployment/docker/`：backend/gateway/backend/infrastructure/nodes/edge/infrastructure/nodes/cloud/monitor 镜像。
- `infrastructure/delivery/deployment/docker-compose.yaml` 本地一键起栈。

## 开发循环
1. 读 developer/ 与目标 AGENT.md
2. 改代码 -> 跑测试 -> 更新文档与 CHANGELOG -> 提交
