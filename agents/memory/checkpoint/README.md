# agents/memory/checkpoint — 检查点

> 记忆子系统的 `检查点` 子模块（隶属 agents/ 智能体域）。开发前阅读 `agents/memory/AGENT.md` 与 `developer/MEMORY_GUIDE.md`。

## 职责
状态保存与恢复：支持任务挂起/恢复与容错。

## 接口契约
统一通过 `protocol/memory.py` 的 `MemoryPacket` 读写，禁止子模块自造结构。

## 输入
- 来自上游模块的 `MemoryPacket`（working/semantic/episodic/archive/embedding/summary/compression 字段）。

## 输出
- 检索结果、压缩摘要、同步状态等，封装为 `MemoryPacket` 或 `Event(MemoryUpdate)`。

## 依赖
- `protocol/`、`tooling/configs/` 索引与淘汰策略配置。

## 测试
`pytest tests/agents/memory/checkpoint/`。
