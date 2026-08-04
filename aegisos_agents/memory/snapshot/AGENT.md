# Agents/Memory/Snapshot — AGENT.md

> 本文件是 `aegisos_agents/memory/snapshot/` 模块的开发规范。

## 职责
全局状态快照：定期拍摄 MemoryStore + 编排器拓扑快照，为 replay/monitor 提供时间线数据源。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `manager.py` — SnapshotManager

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`capture(label, state)` / `restore(snapshot_id)` / `list_snapshots(session_id)` / `prune(session_id, keep)` / `stats()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_snapshot.py`

## H2 升级路径
对接 observability/inspect/replay/ 播放器，按快照时间线跳转。
