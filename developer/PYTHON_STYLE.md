# PYTHON_STYLE.md — Python 风格规范

> 后端与各 Python 子系统统一风格。

## 基线
- Python 3.11+；遵循 PEP 8 + PEP 484 类型注解。
- 格式化：`ruff format`；检查：`ruff check` + `mypy`。
- 导入：标准库 -> 三方 -> 本项目；分组排序。

## 类型
- 所有公共函数/方法标注参数与返回类型。
- 协议数据类使用 `@dataclass`（见 `protocol/`）。
- 避免 `Any`；确需时加注释说明。

## 异步
- I/O 密集子系统（agents/planning/engine/eventbus/infrastructure/transport/communication/agents/tools/llms/gateway）使用 `asyncio`。
- 不在异步路径中同步阻塞；重活放线程池/队列。

## 项目布局
- 每个子系统包含 `__init__.py` 导出公共接口。
- 实现与接口分离：复杂模块提供 `interfaces.py` 或在 AGENT.md 声明接口。

## 错误
- 自定义异常继承统一基类（如 `AegisError`）。
- 校验失败抛 `ValueError`/自定义校验异常。

## 测试
- `pytest`；用 `tests/{module}/` 镜像结构。
- 使用 fixtures（`tests/fixtures/`）；不依赖外部网络。

## 工具链
- `ruff format && ruff check --fix && mypy && pytest` 为提交前必跑。
