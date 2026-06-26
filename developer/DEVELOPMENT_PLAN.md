# DEVELOPMENT_PLAN.md — 开发计划

> 与 ROADMAP.md 对齐，面向执行的开发计划。Agent 据此安排迭代。

## 总策略
自底向上 + 契约先行：先 protocol，再 memory，再 router，再 scheduler，再 planner+agents，再 frontend，最后 deployment。

## 阶段任务（与 developer/roadmap/P* 一一对应）
- **P0**：目录骨架、AGENT.md 体系、developer 规范、CI 空壳。
- **P1**：protocol/*.py 全部数据类 + 序列化 + schema 校验 + 往返测试。
- **P2**：memory 12 子模块 + 统一 MemoryPacket 接口 + 检索/压缩/同步。
- **P3**：topology 图构建 + router 动态低熵路由 + GraphUpdate。
- **P4**：scheduler 多级队列 + 依赖/资源/信任调度 + 重试/抢占。
- **P5**：planner DAG + agents 10 角色 + runtime 生命周期 + 端到端任务。
- **P6**：frontend 画布/图谱/监控/回放 + backend API + WS/SSE 实时。
- **P7**：deployment docker/k8s/ci + scripts 一键化 + 冒烟。

## 每阶段交付物
代码 + 测试（tests/）+ 文档更新（docs/、CHANGELOG）+ AGENT.md 同步。

## 风险与缓解
- 协议频繁变更 -> P1 先冻结契约骨架。
- 图一致性 -> P3 用事件流驱动 GraphUpdate，单调更新。
- Agent 协作不稳定 -> P5 反思 + 信任度反馈闭环。

## 验收门禁
每阶段需通过：单元测试 + 集成测试 + 对应 ROADMAP 完成标准。
