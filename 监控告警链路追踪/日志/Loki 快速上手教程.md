---
publish: true
tags:
  - Loki
  - 部署
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/get-started/quick-start/tutorial/

用 Docker Compose 在本机跑通 **Alloy → Loki → Grafana** 的最小链路，并用 LogQL 查询示例应用（greenhouse）的日志。概念见 [[Loki 概述]]，语法见 [[LogQL 日志查询]]、[[LogQL 指标查询]]。

前置条件：Docker、Docker Compose、Linux 或 macOS（Windows 需 WSL）。

## 架构与端口

```
greenhouse 微服务容器 ──(docker.sock)──> Alloy ──push──> Loki ──> Grafana
```

| 组件 | 地址 | 作用 |
|---|---|---|
| Grafana | http://localhost:3000 | 查询与可视化 |
| Loki | http://localhost:3100/metrics | 日志存储与聚合 |
| Alloy | http://localhost:12345/graph | 采集与转发（含 live debugging） |
| Greenhouse | http://localhost:5005 | 示例微服务应用 |
| 日志钻取 | http://localhost:3000/drilldown | Grafana 的日志探索页 |

## 步骤

### 1. 部署 Loki 栈

```bash
git clone https://github.com/grafana/loki-fundamentals.git -b getting-started
cd loki-fundamentals
docker compose up -d
```

预期看到 `grafana`、`loki`、`alloy` 三个容器 `Started`。

### 2. 部署示例应用

```bash
docker compose -f greenhouse/docker-compose-micro.yml up -d --build
```

启动 `main_app`、`plant_service`、`user_service`、`bug_service`、`simulation_service`、`websocket_service`、`db` 共 7 个容器。打开 http://localhost:5005，创建用户、登录、创建植物，产生日志。

## LogQL 查询示例（在 Grafana Explore 中运行）

标签 `container` 由 Alloy 的 relabel 生成，`env="production"` 由 `loki.process` 静态添加（见下文配置）。

### 基础查询

```logql
{container="greenhouse-main_app-1"}                  # 某容器的全部日志
{container="greenhouse-main_app-1"} |= "POST"        # 只看包含 POST 的行
```

### 解析

```logql
{container="greenhouse-main_app-1"} | logfmt         # 把 logfmt 键值提取成标签
```

### 排查错误

```logql
{container="greenhouse-plant_service-1"} | logfmt | level="ERROR"
{container="greenhouse-plant_service-1"} | logfmt | level="ERROR", line="58"   # 再限定代码行号
```

### 指标查询（做面板 / 告警）

```logql
# 某服务的错误速率
sum(rate({container="greenhouse-plant_service-1"} | logfmt | level="ERROR" [$__auto]))

# 错误率最高的 10 个服务
topk(10, sum(rate({env="production"} | logfmt | level="ERROR" [5m])) by (service_name))

# 各服务日志吞吐量
sum by (service_name) (rate({env="production"} | logfmt [$__auto]))
```

`$__auto` 是 Grafana 变量，由 Grafana 按面板自动选择区间，只能在 Grafana 里用，直接调 Loki API 要写具体区间。

## 配置解读

### Alloy（`config.alloy`）：发现 → 重标记 → 采集 → 处理 → 写入

```alloy
// 发现 Docker 里的容器
discovery.docker "getting_started" {
	host             = "unix:///var/run/docker.sock"
	refresh_interval = "5s"
}

// 把容器名（去掉前导 "/"）写入 container 标签
discovery.relabel "getting_started" {
	targets = []
	rule {
		source_labels = ["__meta_docker_container_name"]
		regex         = "/(.*)"
		target_label  = "container"
	}
}

// 采集容器日志
loki.source.docker "getting_started" {
	host             = "unix:///var/run/docker.sock"
	targets          = discovery.docker.getting_started.targets
	forward_to       = [loki.process.getting_started.receiver]
	relabel_rules    = discovery.relabel.getting_started.rules
	refresh_interval = "5s"
}

// 处理：这里只加静态标签 env=production
loki.process "getting_started" {
	stage.static_labels {
		values = { env = "production" }
	}
	forward_to = [loki.write.getting_started.receiver]
}

// 写入 Loki
loki.write "getting_started" {
	endpoint {
		url = "http://loki:3100/loki/api/v1/push"
	}
}

// 在 Alloy UI 实时查看日志
livedebugging {
	enabled = true
}
```

这条链路对应 [[Alloy Loki 组件总览]] 里的组件，实战记录见 [[Alloy 采集日志发送到 Loki]]。

### Loki（`loki-config.yaml`）

```yaml
auth_enabled: false                    # 关闭多租户认证，仅限本地
server:
  http_listen_port: 3100
  grpc_listen_port: 9096
common:
  path_prefix: /tmp/loki
  storage:
    filesystem:                        # 本地文件系统存储
      chunks_directory: /tmp/loki/chunks
      rules_directory: /tmp/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
query_range:
  results_cache:
    cache:
      embedded_cache: { enabled: true, max_size_mb: 100 }
limits_config:
  metric_aggregation_enabled: true
  allow_structured_metadata: true
  volume_enabled: true
  retention_period: 24h                # 只保留 24 小时
schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index: { prefix: index_, period: 24h }   # 索引每 24h 一个文件
pattern_ingester:
  enabled: true
ruler:
  enable_alertmanager_discovery: true
  enable_api: true
compactor:
  working_directory: /tmp/loki/retention
  delete_request_store: filesystem
  retention_enabled: true
```

（节选，省略了 `instance_addr`、`log_level`、`frontend` 等项。）要点：单节点、文件系统存储、TSDB + v13 schema、24h 保留期。`index.period: 24h` 正好对应 [[LogQL 查询最佳实践]] 里「每天一个索引文件」（这一对应关系是我的推断，未查证）。

读配置不需要通读参考手册，优先看这几块：`schema_config`、`common.storage`、`limits_config`、`compactor`、`ingester`。教程配置里 `allow_structured_metadata` 和 `volume_enabled` 在新版本中默认就是 `true`，自己搭建时不写也行。想知道任意一项的实际值，用 `curl -s localhost:3100/config | grep ...`，见 [[Loki 配置最佳实践]] 第 6、9 节。

### Grafana 数据源

Grafana 容器启动时用 `entrypoint` 写入 provisioning 文件，自动添加 Loki 数据源：

```yaml
datasources:
- name: Loki
  type: loki
  access: proxy
  url: 'http://loki:3100'
  isDefault: true
```

环境变量里开启了匿名访问：`GF_AUTH_ANONYMOUS_ENABLED=true`、`GF_AUTH_ANONYMOUS_ORG_ROLE=Admin`，`GF_FEATURE_TOGGLES_ENABLE=grafanaManagedRecordingRules`。

## 完整的 MLT 示例

教程末尾只是指向另一个项目：[grafana/intro-to-mlt](https://github.com/grafana/intro-to-mlt)，是包含 Mimir、Loki、Tempo 和 Grafana 的演示环境（指标、日志、链路追踪，页面标题还提到 profiling），带详细的组件说明和单实例部署配置，也支持推送到 Grafana Cloud。

## 注意

- 这套配置只适合本地演示：`auth_enabled: false`、Grafana 匿名 Admin、24h 保留、文件系统存储，**不要用于生产**。
- 第一个查询用的 `{container=...}` 依赖 Alloy 生成的 `container` 标签；换成自己的环境要先确认标签名，可在 Explore 的 Label browser 里看。
- 内容基于 WebFetch 摘要，Loki 配置是节选，完整内容以仓库中的文件为准。
