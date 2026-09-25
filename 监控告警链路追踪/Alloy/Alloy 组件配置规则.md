---
publish: true
---

承接 [[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]]，那篇讲的是语法长什么样，这篇讲组件配置的具体规则：参数分类、多实例、依赖关系、循环防护。

## 必填参数 vs 可选参数

组件的 Arguments 分两种，可选参数不设置时用默认值：

```alloy
local.file "targets" {
  filename       = "/etc/alloy/targets"  // 必填参数，不写会报错
  poll_frequency = "1m"                  // 可选参数，默认值通常是几秒到几分钟级别
  is_secret      = false                 // 可选参数
}
```

每个字段都有明确的类型定义，赋值前 Alloy 会做类型检查，类型不对直接报配置错误。

## 嵌套配置块的完整形态

以 `prometheus.remote_write` 为例，一个组件内可以套多层嵌套块，各自管不同的关注点（认证、发送队列）：

```alloy
prometheus.remote_write "production" {
  endpoint {
    url = "https://prometheus.example.com/api/v1/write"

    basic_auth {
      username      = "metrics"
      password_file = "/etc/secrets/password"   // 也可以直接给文件路径，不一定要引用组件
    }
  }

  queue_config {
    capacity             = 10000
    batch_send_deadline  = "5s"
  }
}
```

## 组件引用与动态更新

引用语法固定为 `组件类型.标签.导出名`：

```alloy
local.file "api_key" {
  filename = "/etc/secrets/api.key"
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
```

关键行为：**文件内容变化 → `local.file` 的导出值更新 → 下游 `prometheus.remote_write` 自动拿到新值**，不需要重启 Alloy。这个自动传播是靠"组件控制器"实现的——它负责调度组件执行、上报健康/调试状态、在依赖变化时重新求值参数、维护导出值。本质上组件之间是一张依赖图，控制器按依赖关系做增量更新。

**引用只能写在两个地方**：组件的参数（Arguments）里，或者嵌套配置块的字段里，不能写在别的地方（比如不能作为顶层独立语句、不能出现在块的 label 位置）。

**求值顺序**是按依赖图拓扑排序来的，三步走（对应下面这个例子）：

```alloy
local.file "target" {
  filename = "/etc/alloy/target"
}

prometheus.scrape "default" {
  targets    = [{ "__address__" = local.file.target.content }]
  forward_to = [prometheus.remote_write.onprem.receiver]
}

prometheus.remote_write "onprem" {
  endpoint {
    url = "http://prometheus:9009/api/v1/push"
  }
}
```

1. 先求值没有依赖的组件（`local.file.target`）
2. 再求值依赖它的组件（`prometheus.scrape.default`，用文件内容当 target）
3. 最后求值链路末端（`prometheus.remote_write.onprem`）

`local.file` 内容变化时，只会触发下游 `prometheus.scrape` 重新求值，不会把整张图重新跑一遍——这也是为什么组件多了以后 Alloy 更新配置很快，属于增量重新求值而不是全量重启。

## 循环引用防护

Alloy 会检测依赖图里的环，配置阶段直接拒绝，防止无限循环求值：

```alloy
// 无效：自己引用自己
local.file "self_reference" {
  filename = local.file.self_reference.content
}

// 无效：A 依赖 B，B 又依赖 A
local.file "a" {
  filename = local.file.b.content
}
local.file "b" {
  filename = local.file.a.content
}
```

## 多实例管理

同一组件类型可以起多个实例，靠不同 label 区分，各自独立运行、独立维护自己的健康状态，互不干扰：

```alloy
prometheus.scrape "api" {
  targets    = [{"__address__" = "api.example.com:8080"}]
  forward_to = [prometheus.remote_write.production.receiver]
}

prometheus.scrape "database" {
  targets    = [{"__address__" = "db.example.com:9090"}]
  forward_to = [prometheus.remote_write.production.receiver]
}
```

两个实例可以转发到同一个下游（`prometheus.remote_write.production`），下游会收到两路数据。

## 小结

组件配置本质是在声明一张有向无环依赖图：**参数决定组件怎么跑，导出决定别人能拿到什么，控制器负责在依赖变化时做增量重新求值**，循环引用在配置阶段就被拒绝，不会跑到运行时才发现死循环。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]] — Block/Attribute/Expression 语法基础
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — Alloy 整体定位
