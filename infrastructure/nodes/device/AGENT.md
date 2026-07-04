# Infra/Device 端侧 — AGENT.md

> 本文件是 `infrastructure/nodes/device/` 模块的开发规范。AI 开发本模块前**必须先阅读本文件**，再阅读 `developer/specs/01_ARCHITECTURE_SPEC.md` 相关章节。

## 职责
**端侧节点（Device/Terminal）**：终端设备上的超低延迟、隐私敏感任务处理。包括本地告警分诊、协议异常检测、轻量 IDS、数据采集。

### 端侧典型设备

| 设备类型 | 示例 | 模型/引擎 | 攻防用途 |
|---------|------|----------|---------|
| PC / 笔记本 | 员工电脑、安全分析师工作站 | 规则引擎 / 1-3B 小模型 | 端点检测（EDR）、进程异常告警 |
| 手机 / 平板 | 移动设备 | 嵌入式模型 / 纯采集 | 移动端 MDM 告警、网络行为采集 |
| IoT 传感器 | 摄像头、门禁、工控传感器 | 规则引擎 | 协议异常检测、设备指纹采集 |
| 防火墙盒子 | 网络设备 | 嵌入式 IDS | 本地流量过滤、IP 封禁 |
| 工控终端 | SCADA / PLC | 规则引擎 | 工控协议异常检测 |

### 端侧 vs 边侧 vs 云侧

| 维度 | 端侧 (device/) | 边侧 (edge/) | 云侧 (cloud/) |
|------|---------------|-------------|--------------|
| 物理形态 | PC / 手机 / IoT / 防火墙盒子 | 边缘网关 / 机架服务器 | GPU 集群 / 厂家 API |
| 算力 | 极弱（规则引擎/1-3B） | 中等（7-14B） | 强（70B+/GPT-4o） |
| 延迟 | <100ms | <1s | 1-5s |
| 隐私 | 完全本地 | 区域隔离 | 可脱敏 |
| 调度规则 | privacy=local 或 latency<1s | latency<5s | 默认 |

## 读取目录（允许读）
- protocol/
- infrastructure/transport/communication/
- tooling/configs/
- developer/

## 禁止修改目录
- infrastructure/nodes/edge/ 边侧实现
- infrastructure/nodes/cloud/ 云侧部署
- frontend/
- protocol/ 类型定义

## 输出
- infrastructure/nodes/device/runtime/ — 端侧轻量运行时（规则引擎/嵌入式小模型）
- infrastructure/nodes/device/collect/ — 数据采集（进程/端口/流量/日志）
- infrastructure/nodes/device/sync/ — 断连续传（离线优先，按需上报）

## 依赖
- infrastructure/transport/communication/ 通道（MQTT/CoAP 轻量信令）
- protocol/ Sync

## 接口
端边云协同的最底层节点；离线优先，数据按需上报到边侧。

## 测试方式
`pytest tests/infrastructure/nodes/device/`，覆盖核心路径与边界条件，覆盖率目标 >= 80%。

## 日志位置
`logs/infrastructure/nodes/device/`（结构化 JSON 日志，按 session/task 切分）。

## 配置位置
`tooling/configs/device.yaml`（环境差异通过 tooling/configs/environments/ 覆盖）。

## 开发约定
- 遵循 `developer/specs/11_AI_CODING_SPEC.md` 与 `developer/specs/12_TECH_STACK_SPEC.md`。
- 所有对外数据结构必须复用 `protocol/` 定义的类型，禁止自造并行结构。
- 对外通信一律走 `protocol/message.py` 的 Message 信封，禁止裸 JSON。
- 提交前运行本模块测试并更新 `developer/CHANGELOG.md`。
- 修改前确认本模块在分层中的位置（见 `developer/specs/02_DIRECTORY_SPEC.md`），不得越界。

## 交叉引用（去哪里找）
- **本模块规范**：developer/specs/01_ARCHITECTURE_SPEC.md + 12_TECH_STACK_SPEC.md
- **API 边界**：infrastructure/api/ — from infrastructure.api import ...
- **数据契约**：protocol/message.py / protocol/sync.py
- **调度算法**：agents/planning/engine/scheduler/ — tier="device" 对应本层
- **相关计划**：developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H1 沙箱靶场/端边云）
