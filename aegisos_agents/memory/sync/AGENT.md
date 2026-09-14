# Agents/Memory/Sync — AGENT.md

> 本文件是 `aegisos_agents/memory/sync/` 模块的开发规范。

## 职责
端边云记忆同步：push/pull/merge 协议骨架，当前进程内多节点模拟，为 H7 容器化预留 gRPC/WebSocket 升级路径。

## 读取目录（允许读）
- protocol/

## 禁止修改目录
- protocol/ 类型定义
- aegisos_agents/memory/ 其他子模块

## 输出
- `sync.py` — MemorySync

## 依赖
- protocol/memory.py MemoryPacket

## 接口
`register_node(node_id, role)` / `unregister_node(node_id)` / `push(node_id, packets)` / `pull(node_id, since)` / `merge(local, remote)` / `list_nodes()`

## 测试方式
`pytest tests/aegisos_agents/memory/test_sync.py`

## H7 升级路径
替换 push/pull 底层为 gRPC/WebSocket 传输，接口签名不变。
