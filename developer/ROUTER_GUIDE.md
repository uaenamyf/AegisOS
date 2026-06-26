# ROUTER_GUIDE.md — 动态图路由规范

> 路由位于 `agents/planning/engine/router/`，拓扑构建位于 `agents/planning/engine/topology/`。这是赛题核心亮点：动态异构群体智能 + 低熵通信。

## 流程
```
Task -> Semantic Graph -> Agent Graph -> Dynamic Routing
  -> Sparse Communication -> Adaptive Graph -> Graph Update
```

## 节点与边
- 节点类型：Agent Node / Task Node / Memory Node / Tool Node
- 边属性：weight / entropy / latency / trust_score / success_rate

## 路由目标
- 最小化通信熵（低熵稀疏通信）。
- 选择高 trust_score、高 success_rate、低 latency 的链路。
- 动态计算链路而非全广播：
  ```
  AgentA -> Planner -> Memory -> Coder -> Reviewer -> Executor
  ```

## 自适应
- 任务完成后用结果更新边属性（成功率/延迟/信任度）。
- 产出 `GraphUpdate` 事件（EVENT_SPEC），topology 应用变更。

## 异构
- 不同类型节点能力差异建模为节点属性；路由按能力匹配。

## 接口
- `route(task) -> Route`：返回稀疏通信链。
- `update_graph(diff) -> ack`：应用图变更。

## 测试
- 路由决策确定性测试 + 图更新一致性测试 + 熵度量测试（对齐 evaluation）。
