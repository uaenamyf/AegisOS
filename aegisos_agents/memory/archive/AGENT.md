# Agents/Memory/Archive — AGENT.md

> 本文件是 `aegisos_agents/memory/archive/` 模块的开发规范。

## 职责
冷数据归档：低引用频次的历史经验从 episodic 下沉长期保存，支持回热（defrost）。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/episodic/（defrost 回写）

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `store.py` — ArchiveStore

## 依赖
- protocol/memory.py MemoryPacket
- aegisos_agents/memory/episodic/store.py EpisodicMemory（defrost 回写引用）

## 接口
`archive(packets)` / `recall(task_id)` / `defrost(task_id, episodic)` / `search(keyword)` / `size()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_archive.py`

## H2 升级路径
替换 `_store: list` 为文件/SQLite 持久化，接口不变。
