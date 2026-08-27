# P7-Extended 端边侧模块深度任务拆解与优化报告

> **文档性质**：P7 端边云任务线的「端边侧」聚焦补充档案。原 `P7-端边云-任务切分与执行报告.md` 是全局 12 轮总纲，**本文件聚焦端边侧（R3-R9）的细化拆解**，每模块补充优化评估、可行性分析、开工前详细设计。
>
> **创建日期**：2026-08-27
> **最后更新**：2026-08-27
> **维护规则**：每轮完工后更新对应模块的「完工后报告」段；版本回退时本文件随仓库回退。

---

## §0 现状总览

### 0.1 已完成（R0-R2）

| 轮次 | 产出 | 测试 | commit |
|------|------|------|--------|
| R0 | git init + 基线快照 | — | `473025c` / `38e2a2d` |
| R1 | NodeProfile + infrastructure.yaml + descriptor.py | 15 | `4c3fc64` |
| R2 | DeviceNode + BaseHttpNode + InferenceResult + scheduler 降级修复 | 21 | `2ea22e9` / `0a66dcd` |

### 0.2 待完成（R3-R12）

| 轮次 | 名称 | 当前状态 | 优化空间 |
|------|------|----------|----------|
| **R3** | 边侧节点运行时 | `edge/` 仅 AGENT.md | ⭐⭐⭐ 中等 |
| **R4** | 云侧节点运行时 | `cloud/` 仅 AGENT.md | ⭐⭐ 较小 |
| **R5** | 节点注册中心与心跳探活 | 零代码 | ⭐⭐⭐ 中等 |
| **R6** | 执行派发器 | 零代码 | ⭐⭐⭐⭐ 较大 |
| **R7** | 数据敏感等级自动分级 | 零代码 | ⭐⭐⭐ 中等 |
| **R8** | 级联推理 + 分段流水线 | 零代码 | ⭐⭐⭐⭐⭐ 最大 |
| **R9** | 记忆同步向量时钟 | 有基础实现 | ⭐⭐ 较小 |
| **R10** | 后端 API 暴露 | 零代码 | ⭐ 标准 |
| **R11** | 前端可视化 | 零代码 | ⭐⭐ 较小 |
| **R12** | 端到端演示 + Benchmark | 零代码 | ⭐ 标准 |

---

## §1 逐模块深度拆解与优化评估

---

### R3 —— 边侧节点运行时（EdgeNode）

#### 1.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 高。BaseHttpNode 已提供 `_post_json`/`_get_json`/`_timed_infer` 底座，EdgeNode 直接继承 | 服务器不可达时需降级到 cloud |
| 比赛贴合度 | ✅ 直接对应 C-1「适配边缘异构算力」 | 演示时需一台可访问的服务器 |
| 与现有代码衔接 | ✅ 与 DeviceNode 同构，R1 NodeProfile 已定义 edge 档案 | provider 分支需新增 aegis_edge 协议 |

#### 1.2 优化评估

**原计划**（来自 P7 报告 R3 开工前报告）：
- EdgeNode 支持两种 provider：ollama + aegis_edge
- edge_server.py 约 80 行 stdlib HTTP 服务
- deploy_edge.ps1 部署脚本

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R3-1** | 增加 EdgeNode 本地 Mock 模式 | 无服务器时也能演示边侧逻辑（用于 R12 演示幕3 的降级场景） | 演示容错 |
| **O-R3-2** | edge_server.py 增加区域聚合缓存 | 原计划已有，但需明确：同 prompt+model 的短 TTL 缓存（如 60s），体现"区域聚合"的差异化价值 | 性能加分 |
| **O-R3-3** | 增加 `latency_ms` 主动上报 | edge_server 每次推理后把延迟写入响应头，EdgeNode 解析作为注册中心后续的延迟排序依据 | R5/R6 联动 |
| **O-R3-4** | edge_server.py 增加 `/models` 端点 | 返回可用模型列表，方便 R5 注册中心动态发现 | 可扩展性 |

**结论**：原计划足够好，O-R3-1 和 O-R3-2 强烈建议加入，O-R3-3 和 O-R3-4 按需（R5 时再补也不迟）。

#### 1.3 细化后的任务清单

```
R3.1  EdgeNode 类实现（infrastructure/nodes/edge/edge_node.py）
       - 继承 BaseHttpNode
       - provider=ollama：复用 DeviceNode 的 Ollama REST 协议
       - provider=aegis_edge：POST /infer + GET /health
       - health() 方法（双协议分支）
       - infer() 方法（双协议分支）
       - 本地 Mock 模式（O-R3-1）

R3.2  edge_server.py 边缘服务（tooling/scripts/edge_server.py）
       - stdlib http.server，零依赖
       - POST /infer：转发到本地 Ollama
       - GET /health：返回 200
       - 区域聚合缓存（同 prompt+model 60s TTL）（O-R3-2）
       - 延迟上报响应头（O-R3-3）

R3.3  deploy_edge.ps1 部署脚本（tooling/scripts/deploy_edge.ps1）
       - scp edge_server.py 到服务器
       - 远程 nohup 拉起
       - 服务器不可达时友好提示

R3.4  测试（tests/infrastructure/nodes/edge/）
       - test_edge_node_ollama.py：mock Ollama HTTP
       - test_edge_node_aegis_edge.py：mock aegis_edge HTTP
       - test_edge_node_mock.py：mock 模式
       - test_edge_server.py：本地起停集成测试
```

#### 1.4 内部逻辑（数据流）

```
EdgeNode.infer(prompt)
  → 判断 provider 分支
  → ollama: POST /api/generate（与 DeviceNode 同协议）
  → aegis_edge: POST /infer（JSON: prompt/system/max_tokens → {text, usage}）
  → mock: 返回固定文本（模拟边缘推理结果）
  → 统一组装 InferenceResult

edge_server.py 主循环
  → GET /health → 200
  → POST /infer → 查缓存 → 命中则返回 → 未命中则转发 Ollama → 写缓存 → 返回
```

---

### R4 —— 云侧节点运行时（CloudNode）

#### 2.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 极高。`aegisos_agents/tools/llms/sdk_provider.py` 已有 SDK 通路 | API Key 缺失时需 Mock 降级 |
| 比赛贴合度 | ✅ 直接对应 C-5「充分利用云端算力」 | 无网络时依赖 Mock |
| 与现有代码衔接 | ✅ 环境变量 OPENAI_BASE_URL/OPENAI_API_KEY 沿用 | 需确认 SDK 同步调用方式 |

#### 2.2 优化评估

**原计划**：
- 包装 `OpenAI().chat.completions.create()` 为同步调用
- Mock 降级
- 重试一次（指数退避 1s）

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R4-1** | usage 字段细分 | 除 prompt/completion tokens 外，额外记录 `model` 字段（展示具体用了哪个云模型） | R12 benchmark 数据更丰富 |
| **O-R4-2** | 支持 system prompt | 现有 DeviceNode 已支持 system 参数，CloudNode 同步支持 | 接口一致性 |
| **O-R4-3** | 增加 `stream=False` 显式声明 | OpenAI SDK 默认 stream，显式关闭以防意外 | 稳定性 |

**结论**：原计划足够好，O-R4-1 和 O-R4-2 按需补充，O-R4-3 是防御性编程。

#### 2.3 细化后的任务清单

```
R4.1  CloudNode 类实现（infrastructure/nodes/cloud/cloud_node.py）
       - 持有 NodeProfile
       - health()：验证 API Key 有效性（轻量 GET /models 或等效）
       - infer(prompt, system, temperature, max_tokens, timeout_s)
       - 内部：openai.OpenAI().chat.completions.create()
       - 失败重试：指数退避 1s，最多 1 次
       - Mock 降级：AEGIS_USE_MOCK=true 或 API Key 缺失时返回固定文本

R4.2  测试（tests/infrastructure/nodes/cloud/）
       - test_cloud_node_happy.py：mock OpenAI client
       - test_cloud_node_mock.py：mock 模式
       - test_cloud_node_retry.py：重试逻辑
       - test_cloud_node_error.py：API 错误 → ok=False
```

#### 2.4 内部逻辑

```
CloudNode.infer(prompt, system, temperature, max_tokens)
  → AEGIS_USE_MOCK 或 API Key 缺失？
    → 是：返回 Mock 文本（"CloudNode Mock: 这是云端大模型对'{prompt[:50]}...'的回复"）
    → 否：构造 messages=[{role:"system", content:system}, {role:"user", content:prompt}]
      → client.chat.completions.create(model, messages, temperature, max_tokens, stream=False)
      → 成功：解析 choices[0].message.content + usage
      → 失败：重试一次（sleep 1s）→ 再失败则 ok=False
  → 组装 InferenceResult
```

---

### R5 —— 节点注册中心与心跳探活

#### 3.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 高。纯内存数据结构 + daemon 线程 | 多线程安全需注意 |
| 比赛贴合度 | ✅ 直接对应交付物 e「接受节点失效无人工干预自主完成」 | 心跳时序需与 R6 降级联动 |
| 与现有代码衔接 | ✅ 消费 R1 NodeProfile.to_registry_dict()；实现 NodeRegistryAPI | infrastructure/api 的 Protocol 需兑现 |

#### 3.2 优化评估

**原计划**：
- NodeRegistry 类实现 NodeRegistryAPI
- 后台线程心跳探测
- 连续 2 次失败标记 offline
- 事件广播

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R5-1** | 增加「延迟排序」能力 | 不只记录 online/offline，还记录最近一次成功的 `latency_ms`，供 R6 dispatcher 在同等 tier 内选最优节点 | 调度精度 |
| **O-R5-2** | 增加节点「恢复冷却」机制 | 节点从 offline→online 后，先标记为 degraded（5s 冷却），避免抖动 | 稳定性 |
| **O-R5-3** | 注册中心支持动态注册 | 不只在启动时加载 YAML，运行时也可通过 API 注册新节点（R10 端点对接） | 可扩展性 |
| **O-R5-4** | snapshot() 返回结构化 dict | 直接可 JSON 序列化，供 R10 后端和 R11 前端消费 | 集成便利 |

**结论**：原计划框架正确，O-R5-1 和 O-R5-2 是质量提升关键，O-R5-3 先留接口不实现，O-R5-4 是基本要求。

#### 3.3 细化后的任务清单

```
R5.1  NodeRegistry 类（infrastructure/nodes/registry.py）
       - 兑现 NodeRegistryAPI 的 register_node/discover_nodes/heartbeat
       - 内部状态：{node_id: (NodeProfile, status, last_ok_ts, consecutive_failures, last_latency_ms)}
       - register(node_profile)：注册节点
       - discover_nodes(tier, capability)：按条件查询在线节点
       - heartbeat(node_id)：外部调用标记存活
       - snapshot()：全量状态快照（JSON 可序列化）
       - 延迟排序：discover_nodes 支持按 latency_ms 排序（O-R5-1）
       - 恢复冷却：degraded 状态 5s 过渡（O-R5-2）

R5.2  HeartbeatMonitor 后台线程（infrastructure/nodes/registry.py 内嵌）
       - daemon 线程，按 interval_s 周期
       - 逐节点调 health()，记录结果
       - 连续 fail_threshold 次 → offline
       - 恢复 → degraded（冷却）→ online
       - 通过 EventBus 广播 Heartbeat 事件

R5.3  测试（tests/infrastructure/nodes/test_registry.py）
       - 注册/发现/心跳
       - 上线→掉线→恢复三态迁移
       - 延迟排序
       - 假时钟注入（避免真实 sleep）
```

#### 3.4 内部逻辑

```
NodeRegistry 核心状态机：
  online ──(连续 fail_threshold 次失败)──→ offline
  offline ──(health() 恢复)──→ degraded ──(冷却 5s)──→ online

HeartbeatMonitor 线程循环：
  while running:
    for node in registry:
      ok = node.health()
      registry.heartbeat(node_id, ok)
    sleep(interval_s)
```

---

### R6 —— 执行派发器（★ 本任务线枢纽）

#### 4.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 高。核心逻辑是编排已有组件 | 降级链路需穷举测试 |
| 比赛贴合度 | ✅ 直接对应 C-3「自动完成推理位置的动态选择」 | 这是当前最大断裂点 |
| 与现有代码衔接 | ✅ 调度算法(scheduler.py) + 三层节点(R2-R4) + 注册中心(R5) 全部就位 | 需确保 candidates 从 registry 动态获取 |

#### 4.2 优化评估

**原计划**：
- dispatch() 方法：查 registry → 转 Model → 调 schedule() → 执行 infer() → 失败降级重调度
- 返回值附 attempts 轨迹
- 最多 3 次重试

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R6-1** | attempts 轨迹增加 `decision_reason` | 每条 attempt 记录"为什么选这一层"（如 "privacy=local 强制端侧"），答辩时展示决策可解释性 | 答辩素材 |
| **O-R6-2** | 增加「并行探测」模式 | 超低延迟任务（latency_budget < 0.5s）同时向端侧+边侧发请求，取先返回者（race），失败者结果丢弃 | 创新点 |
| **O-R6-3** | 增加 dispatch 历史环形缓冲 | 最近 N 条派发记录（含完整 attempts），供 R10 history 端点消费 | 前端可视化 |
| **O-R6-4** | 降级链增加「同 tier 多节点」支持 | 同一 tier 有多个节点时，先按 latency_ms 排序，逐个尝试再降级到下一 tier | 鲁棒性 |

**结论**：原计划框架正确，O-R6-1 强烈建议（答辩时价值巨大），O-R6-2 是创新亮点但增加复杂度（建议作为可选优化），O-R6-3 是基础设施，O-R6-4 是实用增强。

#### 4.3 细化后的任务清单

```
R6.1  ExecutionDispatcher 类（infrastructure/nodes/dispatcher.py）
       - __init__(registry, nodes: dict[str, DeviceNode|EdgeNode|CloudNode])
       - dispatch(task, prompt, system_prompt, required_capability)
         → 查 registry 在线节点
         → 过滤 enabled + 能力匹配
         → 转 scheduler.Model 候选列表
         → 调 schedule() 得首选 tier
         → 取对应 Node 实例执行 infer()
         → 失败 → 剔除该 tier → 重新 schedule → 重试（最多 3 次）
         → 返回 InferenceResult + attempts 轨迹
       - attempts 轨迹含 decision_reason（O-R6-1）
       - 同 tier 多节点按 latency_ms 排序（O-R6-4）
       - 历史环形缓冲（O-R6-3）

R6.2  测试（tests/infrastructure/nodes/test_dispatcher.py）
       - 正常选云
       - device 失联降级 edge
       - edge 也失联直达 cloud
       - 全部失联返回失败
       - privacy=local 强制端侧
       - 同 tier 多节点择优
       - attempts 轨迹完整性
```

#### 4.4 内部逻辑（核心流程图）

```
dispatch(task, prompt)
  │
  ├─ 1. 查 registry.discover_nodes() → 在线节点
  ├─ 2. 过滤 enabled + capability
  ├─ 3. 转 [scheduler.Model]
  ├─ 4. 调 schedule() → 首选 model
  │
  └─ 5. 执行循环（最多 3 次）
       │
       ├─ 按首选 tier 取 Node 实例
       ├─ node.infer(prompt)
       │   ├─ ok=True → 记录 attempt → 返回 ✅
       │   └─ ok=False → 记录 attempt
       │       ├─ 从候选剔除该 tier
       │       ├─ 重新 schedule（降级）
       │       └─ 继续循环
       │
       └─ 3 次全失败 → 返回失败 ❌
```

---

### R7 —— 数据敏感等级自动分级

#### 5.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 极高。纯函数正则匹配，零依赖 | 中文文本敏感词覆盖可能不全 |
| 比赛贴合度 | ✅ 直接对应 C-2「依据数据敏感等级」 | 攻防场景天然有说服力素材 |
| 与现有代码衔接 | ✅ 放入 engine/scheduler 包内，输入输出是 Task.privacy 字段 | 只升不降策略需保证 |

#### 5.2 优化评估

**原计划**：
- 规则引擎（正则+关键词加权）
- 强规则命中即 local
- 弱规则累计达阈值升 standard→local
- 默认 unrestricted

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R7-1** | 增加中文关键词库 | 中文告警文本、中文攻击日志中的敏感词（如"密码""密钥""内网""漏洞利用代码"） | 准确性 |
| **O-R7-2** | 增加「结构化数据检测」 | JSON/YAML 中包含 credentials/token/api_key 字段 → 自动标记 local | 覆盖面 |
| **O-R7-3** | 增加「文件名/路径检测」 | 输入包含 /etc/shadow、/etc/passwd、.env 等路径 → 敏感 | 覆盖面 |
| **O-R7-4** | 分级结果带置信度 | 返回 (level, confidence, matched_rules) 三元组，供 R6 日志记录 | 可解释性 |

**结论**：原计划框架正确，O-R7-1 和 O-R7-2 是中文场景必备，O-R7-3 是攻防场景加分项，O-R7-4 提升可解释性。

#### 5.3 细化后的任务清单

```
R7.1  PrivacyClassifier 类（aegisos_agents/planning/engine/scheduler/privacy_classifier.py）
       - classify_privacy(text) → (level, confidence, matched_rules)
       - 强规则（命中即 local）：
         - IP 地址（IPv4/IPv6）
         - 内网主机名模式
         - 密码/密钥/token/secret 关键字
         - CVE 编号 + exploit 同现
         - 文件路径 /etc/shadow, /etc/passwd, .env, id_rsa
         - JSON/YAML 中的 credentials 字段
       - 弱规则（累计加权）：
         - 中文：密码/密钥/令牌/漏洞利用/内网/渗透
         - 英文：vulnerability/exploit/payload/backdoor
         - 端口号 + 攻击动词
       - 默认：unrestricted

R7.2  接入点（R6 dispatcher 调用）
       - dispatch() 入口处若 task.privacy == "standard"（未显式声明）→ 自动分类
       - 显式声明 local/unrestricted 的任务尊重原值

R7.3  测试（tests/aegisos_agents/planning/test_privacy_classifier.py）
       - 正例：含 IP 的日志 → local
       - 正例：含密码的告警 → local
       - 正例：CVE 利用代码 → local
       - 反例：普通摘要 → unrestricted
       - 中文文本敏感检测
       - 弱规则累计阈值
       - 置信度输出验证
```

#### 5.4 内部逻辑

```
classify_privacy(text)
  → 强规则扫描（逐个正则匹配）
    → 命中 → 返回 (local, 1.0, [matched_rule])
  → 弱规则加权扫描
    → 分数 ≥ 阈值 → 返回 (local, score/threshold, [matched_rules])
    → 分数 < 阈值 → 返回 (unrestricted, 1.0, [])
```

---

### R8 —— 级联推理 + 分段流水线

#### 6.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 中高。核心是循环调度 + 置信度启发式 | 置信度启发式可能不准确 |
| 比赛贴合度 | ✅ 直接对应 C-4「模型切分」+ 交付物 e | 需在文档中讲清工程取舍 |
| 与现有代码衔接 | ✅ 循环体内调 R6 dispatcher | 不依赖 perception/reflection 代码 |

#### 6.2 优化评估

**原计划**：
- CascadePolicy（enable_cascade / confidence_threshold / max_hops）
- run_cascade()：首跳 device → 置信度不足则 edge → 仍不足则 cloud
- 置信度启发式：输出长度异常截断、自评 prompt、JSON 可解析性
- segment_pipeline()：端侧分块脱敏 → 云侧综合

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R8-1** | 级联策略可配置化 | 不同场景用不同级联链（如隐私场景 device→edge→cloud，性能场景 cloud→edge→device） | 灵活性 |
| **O-R8-2** | 增加「token 节省统计」 | 每次级联记录实际消耗 vs 全走云的理论消耗，输出节省比例 | R12 benchmark 数据 |
| **O-R8-3** | 置信度启发式增加「model 自评」 | 让当前层模型以 1-10 给自己打分（"你对这个回答的置信度是多少？"），低分升级 | 准确性 |
| **O-R8-4** | 分段流水线增加「重叠摘要」 | 相邻块之间保留 20% 重叠，避免边界信息丢失 | 质量 |

**结论**：原计划框架正确，O-R8-1 是灵活性的关键，O-R8-2 直接对应评分表「资源效率」，O-R8-3 提升置信度判断准确性，O-R8-4 提升分段流水线质量。

#### 6.3 细化后的任务清单

```
R8.1  CascadePolicy 与 run_cascade()（aegisos_agents/planning/engine/scheduler/cascade.py）
       - CascadePolicy dataclass：enable_cascade, confidence_threshold, max_hops, chain
       - run_cascade(dispatcher, task, prompt, policy)
         → 按 chain 顺序逐跳执行
         → 每跳后用置信度启发式判断
         → 高置信 → 返回（低层成功）
         → 低置信 → 升级到下一跳
         → max_hops 截断
       - 置信度启发式：
         a. 输出长度 < 20 字符 → 低置信（截断）
         b. 输出含 "I don't know" / "无法" / "不确定" → 低置信
         c. JSON 可解析性检查（若期望 JSON 输出）
         d. 模型自评 prompt（O-R8-3）
       - Token 节省统计（O-R8-2）

R8.2  segment_pipeline() 分段流水线
       - 端侧：split_text() → 分块 + 敏感脱敏（复用 R7 正则）
       - 边侧（可选）：中间块摘要
       - 云侧：综合脱敏摘要做全局推理
       - 伪代码 + 复杂性分析写入 docs/

R8.3  技术文档产出（docs/端边云协同技术方案.md）
       - 模型切分概念澄清（层间切分 vs 任务级切分）
       - 级联推理算法伪代码 + 复杂性分析
       - 分段流水线伪代码 + 通信量分析

R8.4  测试（tests/aegisos_agents/planning/test_cascade.py）
       - 首跳高置信不升级
       - 低置信逐级升级
       - max_hops 截断
       - token 节省统计
       - 分段流水线分块/脱敏
```

#### 6.4 内部逻辑

```
run_cascade(dispatcher, task, prompt, policy):
  total_tokens = 0
  cloud_theoretical_tokens = estimate_cloud_tokens(prompt)  # 全走云的理论消耗

  for hop in policy.chain:
    result = dispatcher.dispatch(task, prompt, required_capability=hop.capability)
    total_tokens += result.usage.total_tokens
    confidence = assess_confidence(result.text, task)
    
    if confidence >= policy.confidence_threshold:
      return result + {saved_tokens: cloud_theoretical_tokens - total_tokens}
    
    if hop == policy.chain[-1]:  # 最后一跳
      return result  # 即使低置信也不再升级

  return last_result  # max_hops 截断
```

---

### R9 —— 记忆同步启用向量时钟

#### 7.1 可行性评估

| 维度 | 评估 | 风险 |
|------|------|------|
| 技术可行性 | ✅ 极高。经典 10 行算法，纯函数 | 需保持现有 6 个测试不破坏 |
| 比赛贴合度 | ✅ 对应答题要求 a「分布式记忆一致性」 | 修复 spec 与实现的落差 |
| 与现有代码衔接 | ✅ 改造 `aegisos_agents/memory/sync/sync.py`，不改变方法签名 | 协议层 SyncPacket 已定义 vector_clock |

#### 7.2 优化评估

**原计划**：
- push 时递增源节点向量钟分量
- merge 时因果比较（before/after/equal/concurrent）
- 并发冲突用 LWW 兜底
- 保持现有 6 个测试不破坏

**优化点**：

| 编号 | 优化项 | 说明 | 收益 |
|------|--------|------|------|
| **O-R9-1** | 增加「冲突合并日志」 | 并发冲突时记录双发版本到日志，供追溯 | 可观测性 |
| **O-R9-2** | 向量时钟可视化 | snapshot() 返回各节点向量钟状态，可 JSON 序列化 | R11 前端展示 |

**结论**：原计划足够好，O-R9-1 和 O-R9-2 是锦上添花。

#### 7.3 细化后任务清单

```
R9.1  向量时钟比较函数（aegisos_agents/memory/sync/sync.py）
       - compare_vc(a: dict, b: dict) → "before"|"after"|"equal"|"concurrent"
       - 纯函数，无副作用

R9.2  MemorySync 升级
       - push() 时递增 self.node_id 分量，携带 vector_clock
       - pull() 时解析对方 vector_clock
       - merge() 时先因果比较 → 支配方直接覆盖 → 并发冲突 LWW 兜底
       - 冲突日志（O-R9-1）

R9.3  测试（tests/aegisos_agents/memory/test_sync_vc.py）
       - 因果：A 先于 B，B 覆盖 A
       - 并发：A 和 B 同时修改，LWW 兜底
       - 等同时：相同版本不覆盖
       - 现有 6 个测试不破坏
```

---

## §2 任务执行顺序与依赖关系

```
R0 ✅ → R1 ✅ → R2 ✅
                    ↓
         ┌─────────┼─────────┐
         ↓         ↓         ↓
        R3        R4        R5（可并行）
       EdgeNode  CloudNode  Registry
         └─────────┼─────────┘
                   ↓
                  R6 ★ (枢纽)
                   ↓
         ┌─────────┼─────────┐
         ↓         ↓         ↓
        R7        R8        R9（可并行）
       Privacy   Cascade   VClock
         └─────────┼─────────┘
                   ↓
                  R10
              Backend API
                   ↓
                  R11
              Frontend Viz
                   ↓
                  R12
              E2E Demo
```

**建议执行顺序**：R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12

其中 R3/R4/R5 可并行，R7/R8/R9 可并行。

---

## §3 全局约束（每轮开工前重读）

1. 所有跨模块数据结构复用 `protocol/`，禁止自造并行结构
2. 跨模块通信走 Message 信封，禁裸 JSON（节点推理 HTTP 是传输细节不受此限）
3. 不修改 `frontend/`（除 R11）、`protocol/` 类型定义、`aegisos_agents/` 业务逻辑（R7/R8/R9 属计划内例外）
4. 新增接口同步更新 `05_API_SPEC.md` 与 `07_EVENT_SPEC.md`
5. 每轮：测试先行（TDD）→ 实现 → 全量回归 `pytest tests/` → 更新本文档 → commit
6. 依赖零新增原则：能用标准库/既有依赖解决就不加包
7. 每轮开工前先更新本文档并单独 commit（便于回退）
8. 每轮完工后再 commit 一次

---

## §4 每轮执行记录模板

每轮开工前，在对应模块下追加：

```markdown
### [轮次] 开工前报告

**要做什么**：（精确到文件、类、方法签名）
**对应比赛什么要求**：（引用赛题原文编号）
**和其它模块的联系**：（输入来自谁、输出给谁、不碰谁）
**内部逻辑**：（数据流图或伪代码）
**验收标准**：（测试用例清单 + 可运行命令）
**优化点落实**：（本模块采纳了哪些优化建议）
```

每轮完工后，在原处追加：

```markdown
### [轮次] 完工后报告

- **实际改动**：（文件清单 + 关键代码说明）
- **改动体现在项目什么地方**：（前端哪里看得到 / 内部调用用在了哪）
- **实测入口**：（精确命令 + 预期输出）
- **测试证据**：（pytest 结果 + 全量回归）
- **commit hash**：（git log 中的 commit）
```

---

> **下一步**：请确认以上任务拆解和优化评估，我将从 R3（边侧节点运行时）开始，先写开工前报告，等你确认后再开干。