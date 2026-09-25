---
publish: true
tags:
  - Alloy
cssclasses:
  - Alloy
---

前面笔记讲的 `local.file`、`prometheus.scrape`、`loki.write` 这些都是**组件**（有 label、能被引用导出值）。这篇讲的是另一类东西——**顶层配置块**：可选、不属于任何组件、每个配置文件最多出现一次、没有 Exports，专门用来配置 Alloy 进程本身的行为（日志怎么打、要不要开调试、配置从哪读）。

## 概览

| 配置块 | 作用 |
| --- | --- |
| `logging` | 配置 Alloy 自身日志的级别/格式/去向 |
| `tracing` | 配置 Alloy 自身的链路追踪（发给 OTel 后端，用于观测 Alloy 自己） |
| `http` | 配置 Alloy 内置 HTTP 服务器（UI、metrics 端点、TLS） |
| `livedebugging` | 开关：是否允许在 UI 里实时看组件数据流 |
| `remotecfg` | 从远程服务器拉取配置，而不是读本地文件 |
| `import.file` / `import.git` / `import.http` / `import.string` | 从文件/Git仓库/HTTP/字符串导入自定义组件 |
| `declare` / `argument` / `export` | 定义自定义组件的三件套（[[监控告警链路追踪/Alloy/Alloy 自定义组件.md]] 已经讲过） |
| `foreach` | 实验性功能，对集合里每个元素动态生成一份组件实例 |

## `logging`：控制 Alloy 自己的日志

```alloy
logging {
  level  = "info"
  format = "logfmt"
}
```

- `level`：`error`/`warn`/`info`（默认）/`debug`
- `format`：`logfmt`（默认，一行一条）或 `json`
- 还能配 `write_to`，把 Alloy 自己的日志也送进 `loki.write`，跟着业务日志一起集中收集——相当于把"监控采集器自己的运行日志"也纳入统一的可观测性体系里

日常调试时把 `level` 调成 `debug`（对应你实际用的 `config.alloy` 顶部那行 `log_level = "debug"`，那是顶层属性的简写，等价于这个 `logging` 块）。

## `http`：Alloy 内置 Web 服务器

控制 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 提到的那个 `127.0.0.1:12345` UI/调试端口的监听地址、TLS 等，默认只监听本地回环地址，不对外网暴露。

## `livedebugging`：⚠️ 默认关闭，之前的排查建议需要补一个前提

```alloy
livedebugging {
  enabled = true
}
```

之前教你在 Alloy UI 里用 **Live Debugging** 功能实时看 `discovery.relabel` 转换前后的数据，这个功能**默认是禁用的**，得先在配置文件里加上这个块并设 `enabled = true`，重载配置后才能在 UI 里看到实时数据流。官方还提示：开启这个功能建议同时在 `http` 块里配好 TLS，因为实时数据流里可能包含敏感信息（比如日志原文）。

## `remotecfg`：从远程拉配置，不是读本地文件

```alloy
remotecfg {
    url = "https://config-server.example.com"
    basic_auth {
        username      = "user"
        password_file = "/path/to/password"
    }
    id             = "collector-1"
    attributes     = {"cluster" = "prod", "env" = "production"}
    poll_frequency = "5m"
}
```

适合大规模场景：中心服务器根据每个 Alloy 实例的 `id`/`attributes` 动态下发不同配置，不用一台台手动改配置文件。**只是想从一个固定 HTTP 地址拉一份静态配置文件，用 `import.http` 就够了，不需要 `remotecfg` 这种带轮询和身份识别的重型方案**——这条判断标准跟之前"要不要用 Alloy"的取舍逻辑是一个道理：先看有没有更轻的选项能解决问题。

## `import.*`：跨文件复用自定义组件

呼应 [[监控告警链路追踪/Alloy/Alloy 自定义组件.md]] 里留的坑——当时说"Module 机制能跨文件共享自定义组件，具体语法没细讲"，这就是那个机制的落地：

```alloy
# module.alloy —— 用 declare 定义组件
declare "add" {
  argument "a" {}
  argument "b" {}
  export "sum" { value = argument.a.value + argument.b.value }
}

# main.alloy —— import.file 导入，用命名空间调用
import.file "math" { filename = "module.alloy" }

math.add "default" { a = 15; b = 45 }
```

`import.file` 从本地文件/目录导入（默认用 `fsnotify` 监听文件变化，改了自动重载，不用手动 `/-/reload`）；`import.git`/`import.http`/`import.string` 分别对应从 Git 仓库、HTTP 地址、字符串变量导入，用法结构一致，只是来源不同。导入之后用 `import.file "math" {}` 里起的命名空间（`math`）当前缀去调用，`math.add "default"` 就是在用导入进来的 `add` 自定义组件。

## `foreach`：对集合批量生成组件实例（实验性功能）

```alloy
foreach "redis" {
    collection = discovery.relabel.redis.output
    var        = "each"
    template {
        prometheus.exporter.redis "default" {
            redis_addr = each["__address__"]
        }
    }
}
```

场景：服务发现出来一堆 Redis 实例，每个实例都要单独起一个 `prometheus.exporter.redis` 去采集——不用手写 N 份配置，`foreach` 遍历 `collection`，`template` 块里的组件定义会针对每个元素动态生成一份实例，`var` 定义的变量（这里是 `each`）在 `template` 内部代表"当前遍历到的这一项"。

限制：只能在 `template` 内部引用外部组件的导出值，不支持反向引用；开启 `enable_metrics` 时，集合元素多了可能导致指标数量爆炸，默认不开。**标了实验性功能**，生产环境用之前留意版本更新说明。

## 小结

这批顶层块解决的是"怎么配置 Alloy 这个程序本身"，跟组件回答"怎么处理数据"是两个层面的问题：`logging`/`http`/`livedebugging` 管 Alloy 自己的可观测性和调试；`remotecfg`/`import.*` 管配置从哪来、怎么复用；`foreach` 管批量生成组件（实验性）。日常最常用的是 `logging`（几乎每份配置都会写）和 `import.file`（一旦要复用自定义组件就用得上），其余几个按需查。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 自定义组件.md]] — declare/argument/export
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 内置 UI/调试端口
