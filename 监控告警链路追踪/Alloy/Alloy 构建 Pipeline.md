---
publish: true
tags:
  - Alloy
---

前面几篇笔记（[[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]]、[[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]]）讲的是单个组件怎么写、组件之间怎么引用。这篇是把散落的组件串成一条**真正干活的采集链路**，对应 get-started 最后一步。

## Pipeline 的本质

> "A pipeline forms when components reference each other's exports."

没有专门的"pipeline"语法，pipeline 就是组件之间通过 `forward_to` / 属性引用连起来自然形成的依赖链，Alloy 在上游导出值变化时沿链路自动重新求值下游（这点在 [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] 已经讲过依赖图机制，这里是它的实际应用）。

## 模式一：线性管道（最简单）

一个数据源直接接一个输出：

```alloy
local.file "api_key" {
  filename = "/etc/secrets/api.key"
}

prometheus.remote_write "production" {
  endpoint {
    url = "http://localhost:9090/api/v1/write"
    basic_auth {
      username = "admin"
      password = local.file.api_key.content
    }
  }
}
```

## 模式二：多阶段管道（服务发现 → 采集 → 转发）

典型的指标采集三段式：

```alloy
discovery.kubernetes "pods" {
  role = "pod"
}

prometheus.scrape "app_metrics" {
  targets    = discovery.kubernetes.pods.targets
  forward_to = [prometheus.remote_write.production.receiver]
}

prometheus.remote_write "production" {
  endpoint {
    url = "https://prometheus.example.com/api/v1/write"
    basic_auth {
      username = "metrics"
      password = local.file.api_key.content
    }
  }
}

local.file "api_key" {
  filename  = "/etc/secrets/api-key"
  is_secret = true
}
```

**顺序无关**：`local.file "api_key"` 写在最后，但不影响执行——这是 [[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]] 里提过的声明式特性的体现，解析器只看依赖图，不看文件里的书写顺序。

## 模式三：日志管道（采集 → 解析富化 → 输出）

日志场景比指标多一道"处理"环节，`loki.process` 里可以叠多个 `stage.*` 子块：

```alloy
loki.source.file "local_files" {
    targets    = [{__path__ = "/var/log/app/*.log"}]
    forward_to = [loki.process.add_labels.receiver]
    file_match {
        enabled     = true
        sync_period = "10s"
    }
}

loki.process "add_labels" {
    stage.logfmt {
        mapping = {
            "extracted_level"   = "level",
            "extracted_service" = "service",
        }
    }
    stage.labels {
        values = {
            "level"   = "extracted_level",
            "service" = "extracted_service",
        }
    }
    forward_to = [loki.write.grafana_cloud.receiver]
}

loki.write "grafana_cloud" {
    endpoint {
        url = "https://logs-prod.grafana.net/loki/api/v1/push"
        basic_auth {
            username = "12345"
            password = local.file.api_key.content
        }
    }
}

local.file "api_key" {
    filename  = "/etc/secrets/loki-key"
    is_secret = true
}
```

`stage.logfmt` 从原始日志行里按 logfmt 格式提取字段，`stage.labels` 把提取出来的字段提升成 Loki 标签，两个 stage 顺序执行，是 `loki.process` 内部的一条子管道。

## 模式四：扇出（一个源 → 多个目标）

`forward_to` 是个数组，写多个 receiver 就能把同一份数据同时发给多个下游（比如同时写生产和预发）：

```alloy
prometheus.scrape "app_metrics" {
  targets = [{"__address__" = "app:8080"}]
  forward_to = [
    prometheus.remote_write.production.receiver,
    prometheus.remote_write.staging.receiver,
  ]
}

prometheus.remote_write "production" {
  endpoint {
    url = "https://prod-prometheus.example.com/api/v1/write"
  }
}

prometheus.remote_write "staging" {
  endpoint {
    url = "https://staging-prometheus.example.com/api/v1/write"
  }
}
```

## 模式五：链式过滤（多阶段处理只保留需要的数据）

`loki.process` 可以一节接一节串联，逐步收窄数据：

```alloy
loki.source.file "raw_logs" {
  targets    = [{"__path__" = "/var/log/app.log"}]
  forward_to = [loki.process.parse.receiver]
}

loki.process "parse" {
  stage.json {
    expressions = {
      level   = "level",
      message = "msg",
    }
  }
  forward_to = [loki.process.filter.receiver]
}

loki.process "filter" {
  stage.match {
    selector = "{level=\"error\"}"
    action   = "keep"
  }
  forward_to = [loki.write.alerts.receiver]
}

loki.write "alerts" {
  endpoint {
    url = "https://loki.example.com/loki/api/v1/push"
  }
}
```

这条链路先解析 JSON 日志，再只保留 `level="error"` 的行，最后单独发到一个"告警用"的 Loki 写入端——即"从全量日志里筛出错误日志单独发一份"这种需求的标准写法。

## 组织建议

- **按逻辑阶段拆分复杂管道**，不要把服务发现、处理、转发全塞进一个巨型组件配置里
- **label 要写清楚语义**：`prometheus.scrape "api_metrics"` 好过 `prometheus.scrape "scraper1"`，排查问题时一眼能看出这个组件是干嘛的
- **密钥用 `is_secret = true`**，防止在 Alloy UI/日志里明文展示（对应 [[监控告警链路追踪/Alloy/Alloy 数据类型.md]] 里的 Secret 类型）

## 调试 Pipeline 的方法

1. 用 Alloy 内置 UI 看组件健康状态，不健康的组件会标红
2. 检查组件导出值是不是预期的数据（UI 里能直接看当前导出内容）
3. 确认 `forward_to` 引用的 receiver 和实际组件对得上
4. 排查是不是出现了循环引用（对应 [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] 里的循环引用防护，Alloy 配置阶段就会拒绝这种配置）
5. 检查配置语法本身有没有写错

## 小结

Pipeline 没有独立语法，就是组件靠 `forward_to`/属性引用手工连出来的依赖图。常见形状：线性（一进一出）、多阶段（发现→采集→转发）、日志处理链（`loki.process` 里叠多个 `stage.*`）、扇出（`forward_to` 数组发多路）、链式过滤（一级级 `loki.process` 收窄数据）。实际部署时几种模式经常混着用。

## 相关笔记

- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]]
- [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] — 依赖图与循环引用防护
- [[监控告警链路追踪/Alloy/Alloy 数据类型.md]] — Secret 类型
