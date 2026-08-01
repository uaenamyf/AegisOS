# Agents/Memory/Checkpoint — AGENT.md

> 本文件是 `aegisos_agents/memory/checkpoint/` 模块的开发规范。

## 职责
任务中断恢复：每 N 步自动保存编排器状态快照，支持断点恢复 + 老检查点清理。

## 读取目录（允许读）
- protocol/
- aegisos_agents/memory/memory_store.py（write-through 引用）

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `manager.py` — CheckpointManager

## 依赖
- protocol/memory.py MemoryPacket
- aegisos_agents/memory/memory_store.py MemoryStore（可选 write-through）

## 接口
`save(session_id, state, label)` / `restore(session_id)` / `list_checkpoints(session_id)` / `prune(session_id, keep_last)` / `maybe_save(session_id, state, interval)`

## 测试方式
`pytest tests/aegisos_agents/memory/test_checkpoint.py`
