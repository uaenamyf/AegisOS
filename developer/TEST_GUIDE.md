# TEST_GUIDE.md — 测试规范

> 测试位于 `tests/`，镜像子系统结构。

## 结构
- `tests/unit/` 单元；`tests/integration/` 集成；`tests/e2e/` 端到端；`tests/fixtures/` 公共夹具；`tests/benchmarks/` 性能。

## 约定
- 框架 `pytest`；异步用 `pytest-asyncio`。
- 不依赖外部网络/真实 LLM；用 fixtures 与 mock。
- 每个公共接口至少一条正路径 + 一条边界/失败路径。
- bug 修复附回归测试。

## 覆盖
- 行覆盖率目标 >= 80%；关键路径（protocol/agents/planning/engine/router/agents/memory/scheduler）>= 90%。
- 覆盖率工具 `coverage` / `pytest-cov`。

## 协议往返测试
- `protocol/` 每个数据类需序列化->反序列化往返 + schema 校验测试。

## 回放与确定性
- e2e 优先基于事件流回放（observability/inspect/replay/）做确定性验证。

## 运行
- `make test`（tooling/scripts/）；CI 在 PR 上自动运行。
