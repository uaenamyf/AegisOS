# DEPLOY_GUIDE.md — 部署规范

> 部署产物在 `infrastructure/delivery/deployment/`，脚本在 `tooling/scripts/`。

## 组件
- `infrastructure/delivery/deployment/docker/`：各服务镜像 Dockerfile + compose。
- `infrastructure/delivery/deployment/k8s/`：编排 manifests（backend/gateway/backend/infrastructure/nodes/edge/infrastructure/nodes/cloud/monitor）。
- `infrastructure/delivery/deployment/ci/`：CI/CD 流水线定义。
- `infrastructure/delivery/deployment/tooling/scripts/`：部署辅助脚本。

## 环境
- `tooling/configs/environments/`：dev/staging/prod 覆盖。
- 密钥走环境变量/Secret，禁止入库。

## 一键命令
- `make setup` 初始化环境
- `make build` 构建镜像/产物
- `make test` 运行测试
- `make deploy ENV=dev` 部署

## 端边云
- 云侧：k8s 部署 backend/gateway/backend/infrastructure/nodes/cloud/monitor。
- 端侧：infrastructure/nodes/edge/ 打包为轻量镜像/二进制，离线优先。
- 同步：protocol/sync.py 协商一致性。

## 可观测
- 部署含 observability/inspect/monitor/（metrics/tracing/alerts）与 observability/inspect/replay/。
- 冒烟：部署后跑 `tests/e2e/` 子集验证。

## 回滚
- 镜像 tag 化；异常按版本回滚；状态走 checkpoint/snapshot 恢复。
