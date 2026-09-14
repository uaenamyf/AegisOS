# XH-202631 比赛专用综合测评报告

**项目**：AegisOS 动态异构群体智能协同推理引擎  
**评估日期**：2026-09-14  
**评估目标**：对照“面向超长程复杂任务的动态异构群体智能架构与深度协同推理”方案，汇总工程回归、确定性架构证据与真实 ARK API 实测结果。

## 1. 结论摘要

本版本已经完成以下可证明能力：

- 感知-规划-执行-记忆-反思闭环；
- 11 个红蓝紫攻防 Agent 的协同编排；
- Top-K 稀疏路由与端-边-云调度；
- 跨轮记忆、压缩、召回、检查点与快照恢复；
- 5/10/20 轮确定性长程任务保持验证；
- 真实火山方舟 OpenAI 兼容 API 的 Chat 和单轮 Drill 验证；
- 真实 AegisOS API 端到端评估 9/9 通过；
- Graph/TaskMap/Monitor/Replay/报告等可解释证据链。

**最终判定**：核心架构、真实 ARK API 链路和演示版要求已达到；真实 5/10/20 轮 LLM 性能与真实端边云网络仍属于待补实测项，不能将 Mock 结果表述为真实生产性能。

## 2. 测试环境

| 类别 | 配置 |
|---|---|
| 标准工程回归 | Python 3.12 / Mock Provider / 测试鉴权 |
| 前端回归 | Vitest / TypeScript / Vite |
| 真实 API | 火山方舟 OpenAI 兼容 Chat Completions |
| 真实模型 | `ark-code-latest` |
| 真实端点 | `https://ark.cn-beijing.volces.com/api/coding/v3` |
| 安全目标 | `10.0.0.0/24` 演示靶场 |
| 真实 Drill | 已完成 1 轮与 2 轮受控验证，目标均为安全演示网段 |

API Key 只保存在本机 `.env`，未写入代码、报告或 Git。

## 3. 工程回归结果

| 项目 | 结果 |
|---|---:|
| Python 全量测试 | **703 passed** |
| 比赛核心专项 | **10 passed** |
| 前端单元测试 | **50 passed** |
| 前端生产构建 | 通过 |
| ESLint | 通过 |
| 低熵广播扫描 | 通过 |
| 真实 API 端到端评估 | **9/9 passed** |

测试过程产生的 SDK 弃用和 tracing 关闭提示不影响测试通过，不作为功能失败。

## 4. 超长程任务确定性证据

评测脚本：`tooling/scripts/run_competition_eval.py`  
报告：`docs/XH-202631-engineering-evidence.md`

评测使用真实 `CyberOrchestrator`、`MemoryStore`、调度器和 `ExecutionDispatcher`，但模型输出使用确定性 Mock，以保证结果可复现。

| 轮数上限 | 实际轮数 | 目标保持率 | 事件同源率 | 记忆隔离率 | 检查点恢复率 | 收敛 |
|---:|---:|---:|---:|---:|---:|---|
| 5 | 5 | 100% | 100% | 100% | 100% | 是 |
| 10 | 10 | 100% | 100% | 100% | 100% | 是 |
| 20 | 20 | 100% | 100% | 100% | 100% | 是 |

验证不变量：

1. 每一轮红队仍绑定同一个目标网段；
2. 蓝队只消费当前轮红队事件；
3. 事件步骤 ID 与当前轮攻击链一致；
4. 工作记忆不会串入其他 Drill；
5. 压缩后的摘要仍属于当前会话；
6. 每轮均有检查点，并可恢复到最后一轮。

## 5. 动态异构路由证据

确定性调度结果：

| 任务约束 | 选择层级 |
|---|---|
| `privacy=local` | device |
| 超低延迟 | device |
| 中低延迟 | edge |
| 高延迟容忍/重计算 | cloud |
| device 失效 | edge 降级 |

本项验证了调度规则、能力过滤和节点失效后的降级链路。真实网络节点联调另行计入限制项。

## 6. 真实 ARK API 实测

### 6.1 Chat 实测

通过 AegisOS `/api/v1/chat`，不是直接绕过系统调用模型。

| 用例 | 结果 | tier | 模型 | 延迟 |
|---|---|---|---|---:|
| 核心能力概述 | 成功 | cloud | `ark-code-latest` | 13.76 s |
| 端边云状态概述 | 成功 | cloud | `ark-code-latest` | 25.74 s |
| 长期记忆与目标一致性说明 | 成功 | edge | `ark-code-latest` | 58.18 s |

结果：**3/3 成功，成功率 100%**，平均延迟约 **32.56 s**。返回中包含真实 provider、model、tier 和执行延迟，证明请求经过 AegisOS 的实际派发链路。

### 6.2 单轮真实 Drill

| 字段 | 结果 |
|---|---|
| Drill ID | `drill-e91603a8` |
| 目标 | `10.0.0.0/24` |
| 最大轮数 | 1 |
| 最终状态 | `done` |
| 实际轮数 | 1 |
| 停止码 | `max_rounds` |
| 总结 | 已生成 |
| 错误 | 空 |

这是一次真实 ARK 驱动的单轮红蓝紫编排验证。`max_rounds` 是人为设置的 1 轮上限，不代表异常或失败。

### 6.3 两轮真实 Drill

第二次受控实测：

| 字段 | 结果 |
|---|---|
| Drill ID | `drill-9da4cf7e` |
| 目标 | `10.0.0.0/24` |
| 最大轮数 | 2 |
| 最终状态 | `done` |
| 实际轮数 | 2 |
| 停止码 | `max_rounds` |
| 错误 | 空 |

两轮真实 ARK 编排耗时较长，但最终正常完成，没有异常退出或超时。当前仍没有进行真实 5/10/20 轮，因为这会显著增加现场 API 延迟和调用成本。

### 6.4 三轮真实 Drill 与结构化输出重试

首次三轮实测在第 2 轮因真实模型结构化输出解析失败而中止：

```text
drill-76bdbc20：aborted，rounds_executed=1，Invalid JSON when parsing model output
```

随后 `StructuredAgent` 增加了一次真实结构化输出重试，并保留纯文本兼容路径的三次重试。修复后重测：

| 字段 | 结果 |
|---|---|
| Drill ID | `drill-5405ae41` |
| 目标 | `10.0.0.0/24` |
| 最大轮数 | 3 |
| 最终状态 | `done` |
| 实际轮数 | 3 |
| 停止码 | `max_rounds` |
| 错误 | 空 |

受控三轮真实 ARK 编排已完成；这仍不等价于真实 5/10/20 轮性能验收。

## 7. 方案要求对照

| 方案关注点 | 当前证据 | 判定 |
|---|---|---|
| 感知-规划-执行-反思闭环 | Agent、Goal、ReAct、Ask、Reflection | 已满足 |
| 动态异构群体 | 11 Agent、Registry、Topology、Top-K | 基本满足 |
| 深度协同推理 | 红蓝紫链、上游产出、紫队反馈 | 已满足 |
| 长程任务保持 | 5/10/20 轮 Mock 不变量 | Mock 范围满足 |
| 长期记忆 | 多层记忆、压缩、召回、checkpoint、snapshot | 已满足 |
| 端边云调度 | 真实调度算法 + Mock 节点失效降级 | 算法满足 |
| 真实端边云网络 | 尚未完成现场网络联调 | 待补实测 |
| 多应用场景 | 网络防御、长程攻击链、端边云协同 | 演示满足 |
| 真实安全工具链 | Docker 基础和隔离网络已配置 | 待补实测 |
| 全链路可解释性 | Graph、TaskMap、Monitor、Replay、报告 | 已满足 |
| 量化证据 | 本报告 + 工程证据报告 | 已建立基线 |

## 8.1 真实 API 端到端评估

评估脚本：`tooling/scripts/run_real_api_eval.py`
评估报告：`docs/XH-202631-real-api-evaluation.md`

本次评估不使用 Docker，直接通过真实运行中的 AegisOS 后端和 ARK Provider 检查：

| 用例 | 结果 |
|---|---|
| 健康检查 | 200 |
| 运行模式/Provider/Model | `real / ark / ark-code-latest` |
| 端边云节点快照 | 200 |
| 普通自然语言 Chat | 200 |
| 系统状态 Chat | 200 |
| 攻防意图安全拦截 | 通过 |
| 会话记忆读取 | 200 |
| Graph 读取 | 200 |
| Drill 历史读取 | 200 |

总计：**9/9 真实 API 用例通过，成功率 100%**。

## 9. 风险与比赛表述边界

真实 ARK Chat 的延迟在本次 9 项评估中约为 9.89-27.27 秒，完整多轮真实 Drill 可能因多个串行 Agent 调用而耗时较长。比赛主演示建议使用确定性 Mock 完成完整多轮闭环，同时用真实 ARK 三轮结果和真实 API 9/9 记录证明真实 Provider 接入能力。

推荐答辩表述：

> AegisOS 已完成动态异构路由、长期记忆、跨轮一致性、红蓝紫协同和真实 OpenAI 兼容 API 接入验证。确定性 Mock 用于保证完整演示可重复，真实火山方舟已完成三轮受控编排验证。真实 5/10/20 轮性能、真实端边云网络及安全工具容器闭环仍需在比赛现场环境继续联调。

禁止表述：

- “Mock 5/10/20 轮结果等于真实模型性能”；
- “真实端边云网络已完成生产级联调”。

## 10. 可重复命令

标准工程回归：

```powershell
$env:AEGIS_USE_MOCK="true"
$env:AEGIS_AUTH_DEFAULT_KEY="aegis-dev-key"
python -m pytest -q
```

确定性比赛证据：

```powershell
python tooling/scripts/run_competition_eval.py --output docs/XH-202631-engineering-evidence.md
```

前端验证：

```powershell
Push-Location frontend
npm test -- --run
npm run build
npm run lint
Pop-Location
```

低熵通信扫描：

```powershell
python tooling/scripts/check_no_broadcast.py --strict
```

真实 API 评估：

```powershell
$env:AEGIS_AUTH_DEFAULT_KEY="aegis-local-demo-key-2026"
python tooling/scripts/run_real_api_eval.py
```