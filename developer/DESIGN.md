# DESIGN.md — 系统设计（SYSTEM_DESIGN）

> 端—边—云协同、调度器、长期记忆、动态图路由、容错恢复等系统级设计。

## 1. 端—边—云协同
- **端（infrastructure/nodes/edge/）**：离线优先，本地推理与轻量调度；资源受限下裁剪上下文。
- **边**：聚合端侧数据，就近推理与缓存。
- **云（infrastructure/nodes/cloud/）**：全局编排、注册中心、重模型服务、全局记忆同步。
- 同步走 `protocol/sync.py`，断连续传 + 一致性协商（最终一致 + 冲突合并）。

## 2. 调度器设计（agents/planning/engine/scheduler/）
- 多级优先队列；按依赖（DAG 拓扑序）+ 资源（CPU/GPU/Token）+ 信任度调度。
- 支持抢占、重试（指数退避）、超时熔断。
- 死锁检测：基于依赖图环检测；饥饿缓解：老化（aging）策略。

## 3. 长期记忆设计（agents/memory/）
- 分层：working（短时）/ episodic（事件序列）/ semantic（知识）/ vector（嵌入）/ archive（冷）。
- 压缩（compression/）：摘要 + 关键信息抽取，在 Token 预算内保留要点。
- 检索（retrieval/）：向量 + 关键词 + 图 多路召回，重排序。
- 反思（agents/perception/reflection/）：失败/成功模式沉淀为经验。
- 检查点（checkpoint/）+ 快照（snapshot/）支持容错与回放。

## 4. 动态图路由设计（agents/planning/engine/router/ + agents/planning/engine/topology/）
- 节点类型：Agent / Task / Memory / Tool。
- 边属性：weight / entropy / latency / trust_score / success_rate。
- 路由目标：最小化通信熵，选择高信任、高成功率、低延迟的稀疏链路。
- 自适应：任务完成后用结果更新边属性，触发 GraphUpdate。
- 异构：不同类型节点能力差异建模为节点属性。

## 5. 容错与恢复
- Task 级：retry + rollback（protocol Task 字段）。
- 状态级：checkpoint + snapshot。
- 系统级：事件流（eventbus）+ replay 确定性回放定位故障。
- Agent 级：心跳（Heartbeat）超时视为失联，调度器重派。

## 6. 可观测与评估
- monitor：指标 + tracing + 告警。
- replay：事件流回放。
- evaluation：任务成功率、通信熵、记忆质量、群体智能指标，对齐赛题评分。

## 7. 安全
- gateway 鉴权 + 限流；工具沙箱（agents/action/execution/executor/sandbox）；密钥走 tooling/configs/environments，禁止入库。
- 日志不记录敏感载荷（payload 脱敏）。
