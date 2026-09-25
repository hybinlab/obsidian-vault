---
publish: true
tags:
  - Alloy
cssclasses:
  - Alloy
---

前面 [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] 讲的是抽象的管道模式，这篇是官方给的 Prometheus 指标采集场景的具体落地配方，三个组件就能跑通：`discovery.*`（发现目标，可选）→ `prometheus.scrape`（抓）→ `prometheus.remote_write`（发）。

## 最小可用配置

```alloy
prometheus.remote_write "default" {
  endpoint {
    url = "http://localhost:9009/api/v1/push"
  }
}

prometheus.scrape "example" {
  targets = [{
    __address__ = "127.0.0.1:12345",
  }]
  forward_to = [prometheus.remote_write.default.receiver]
}
```

支持的写入后端：Prometheus（remote_write 接收端）、Grafana Mimir、Grafana Cloud、Grafana Enterprise Metrics——都是同一套 remote_write 协议，换个 URL 就行。

## 目标发现：Kubernetes 场景

抓 Pod：

```alloy
discovery.kubernetes "pods" {
  role = "pod"

  namespaces {
    own_namespace = false
    names         = ["default"]
  }

  selectors {
    role  = "pod"
    label = "environment in (production)"
  }
}

prometheus.scrape "pods" {
  targets    = discovery.kubernetes.pods.targets
  forward_to = [prometheus.remote_write.default.receiver]
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://localhost:9009/api/v1/push"
  }
}
```

抓 Service 把 `role = "pod"` 换成 `role = "service"`，结构完全一样。

`namespaces` 块控制发现范围：`own_namespace = true` 会把 Alloy 自己所在的命名空间也纳入，`names` 显式指定要扫的命名空间列表。`selectors` 支持两种过滤：`field`（按字段，比如 `metadata.name=my-service`）和 `label`（按标签，比如 `environment in (production, qa)`）。

## 多端点 + 认证（发到 Grafana Cloud 这类需要鉴权的后端）

```alloy
prometheus.remote_write "default" {
  endpoint {
    url = "http://localhost:9009/api/v1/push"
  }

  endpoint {
    url = "https://prometheus-us-central1.grafana.net/api/prom/push"
    basic_auth {
      username = sys.env("REMOTE_WRITE_USERNAME")
      password = sys.env("REMOTE_WRITE_PASSWORD")
    }
  }
}

prometheus.scrape "example" {
  targets    = [{ __address__ = "127.0.0.1:12345" }]
  forward_to = [prometheus.remote_write.default.receiver]
}
```

`endpoint` 块可以重复写多个，同一份抓到的数据会同时发给所有端点——这就是 [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] 里"扇出"模式的另一种实现方式（那篇是用多个 `forward_to`，这里是单个组件内部写多个 `endpoint`）。密码走 `sys.env()` 取环境变量，不硬编码进配置文件，对应 [[监控告警链路追踪/Alloy/Alloy 函数调用.md]] 里的系统函数用法。

## 静态自定义目标：不用服务发现，手写 target 列表

```alloy
prometheus.scrape "custom_targets" {
  targets = [
    {
      __address__ = "prometheus:9090",
    },
    {
      __address__ = "mimir:8080",
      __scheme__  = "https",
    },
    {
      __address__      = "custom-application:80",
      __metrics_path__ = "/custom-metrics-path",
    },
    {
      __address__ = "alloy:12345",
      application = "alloy",
      environment = "production",
    },
  ]
  forward_to = [prometheus.remote_write.default.receiver]
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://localhost:9009/api/v1/push"
  }
}
```

target 对象里几个特殊字段：

| 字段 | 必需 | 作用 |
| --- | --- | --- |
| `__address__` | 是 | `HOST:PORT`，抓取地址 |
| `__scheme__` | 否 | `http`/`https`，不写默认继承 scrape 组件的设置 |
| `__metrics_path__` | 否 | 抓取路径，默认 `/metrics` |

规则：**双下划线开头的字段（`__xxx__`）是元数据，抓取前会被丢弃，不会变成指标的标签**；其他普通 key（比如上面例子里的 `application`、`environment`）会被当成额外标签注入到抓到的每条指标上——这是给指标打自定义标签最直接的方式，不需要额外的 relabel 配置。

## 整体流程

1. 先定 `prometheus.remote_write`，明确指标最终写到哪
2. 用 `discovery.kubernetes`（或直接手写 `targets` 数组）拿到要抓的目标列表
3. `prometheus.scrape` 把目标和写入端连起来
4. 需要过滤目标就在 `discovery.kubernetes` 里加 `namespaces`/`selectors`；需要给指标加自定义标签就直接在 target 对象里加普通字段

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — 多阶段/扇出等通用管道模式
- [[监控告警链路追踪/Alloy/Alloy 函数调用.md]] — `sys.env()` 取环境变量
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 当前 homelab 规模判断为"知识存档，不急着部署"
