---
publish: true
---

对应官方 Processing logs 教程。 [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] 讲的是"怎么把日志采进来"，这篇讲**日志到了 Alloy 之后怎么加工**——`loki.process` 内部怎么叠多个 `stage.*`，从一条原始 JSON 日志里解析字段、改时间戳、按条件丢弃、打标签、替换最终写入内容。

## 核心概念：提取映射表（extracted map）

`loki.process` 内部所有 stage 共享一张"提取映射表"，每个 stage 往里面读/写字段，按**书写顺序从上到下依次执行**——这张表不是日志本身，是处理过程中的临时数据，只有 `stage.output` 才决定最终真正写进 Loki 的日志内容是什么。理解这一点，剩下的 stage 顺序和数据流向就都说得通了。

## 接收日志：`loki.source.api`

教程用的日志源不是文件也不是 Docker，是**直接监听一个 HTTP 端口接收日志推送**：

```alloy
loki.source.api "listener" {
    http {
        listen_address = "127.0.0.1"
        listen_port    = 9999
    }
    labels     = { "source" = "api" }
    forward_to = [loki.process.process_logs.receiver]
}
```

任何能发 HTTP POST 的东西（应用自己的日志 SDK、别的 Alloy 实例的 `loki.write` 出口）都能把日志推给这个端口——这是"多个 Alloy 实例级联"或者"应用直接推日志不落盘"场景的入口组件。

## 待处理的原始日志格式

```json
{
    "log": {
        "is_secret": "true",
        "level": "info",
        "message": "This is a secret message!"
    },
    "timestamp": "2023-11-16T06:01:50Z"
}
```

外层有 `timestamp`，真正的日志内容嵌套在 `log` 对象里，还带了一个 `is_secret` 标记——这条示例日志专门设计成需要"解嵌套 JSON + 按字段过滤 + 改写最终输出"的典型场景。

## 六个 Stage 逐步拆解

```alloy
loki.process "process_logs" {
    // 1. 提取顶层字段
    stage.json {
        expressions = {
            log = "",
            ts  = "timestamp",
        }
    }

    // 2. 解析时间戳
    stage.timestamp {
        source = "ts"
        format = "RFC3339"
    }

    // 3. 解析嵌套 JSON
    stage.json {
        source = "log"
        expressions = {
            is_secret = "",
            level     = "",
            log_line  = "message",
        }
    }

    // 4. 按条件丢弃
    stage.drop {
        source = "is_secret"
        value  = "true"
    }

    // 5. 打标签
    stage.labels {
        values = {
            level = "",
        }
    }

    // 6. 替换最终输出内容
    stage.output {
        source = "log_line"
    }

    stage.static_labels {
        values = {
            source = "demo-api",
        }
    }

    forward_to = [loki.write.local_loki.receiver]
}
```

**第 1 步 `stage.json`**：解析最外层 JSON。`expressions` 里 `log = ""` 表示"把 `log` 字段整个原样取出来"（空字符串表示不做进一步的 JSONPath 提取，留到下一步再处理），`ts = "timestamp"` 表示"从 JSON 的 `timestamp` 字段取值，存进提取映射表的 `ts` 字段"。

**第 2 步 `stage.timestamp`**：从提取映射表里读 `ts` 字段，按 `RFC3339` 格式解析成真正的时间戳，**覆盖这条日志在 Loki 里存储时用的时间**——如果不做这一步，Loki 存的时间戳是 Alloy 收到这条日志的时间，不是日志里记录的原始发生时间，两者在网络延迟或者批量导入历史日志时会对不上。

**第 3 步 `stage.json`（第二次）**：`source = "log"` 表示这次不解析整条原始日志，而是**对第 1 步取出来的 `log` 字段（一个嵌套 JSON 字符串）再做一次 JSON 解析**，提取出 `is_secret`、`level`，以及把内层的 `message` 字段重命名存成 `log_line`。`stage.json` 可以像这样连续叠加，专门用来"逐层剥开嵌套 JSON"。

**第 4 步 `stage.drop`**：检查提取映射表里的 `is_secret` 字段，如果值等于 `"true"`，整条日志直接丢弃、不再往下游转发——用于过滤敏感/不需要的日志，在处理链路里"提前拦截"比进了 Loki 之后再删更省资源。

**第 5 步 `stage.labels`**：把提取映射表里的 `level` 字段提升成正式的 Loki 标签（写法和之前 Docker 教程里的 `stage.labels` 一样，`values` 里的 key 是要提升的字段名，value 留空表示直接用提取映射表里的同名字段）。

	**第 6 步 `stage.output`**：**替换这条日志最终写进 Loki 的正文内容**——不设置这一步的话，Loki 存的还是最原始的那一整条 JSON；设了之后，`source = "log_line"` 表示把提取映射表里 `log_line` 字段的值（也就是最初嵌套在 `log.message` 里的那句话）当成最终日志正文，相当于把一条塞满元数据的 JSON 日志"提纯"成只剩人类关心的那句话。

`stage.static_labels` 和之前笔记里见过的一样，追加一个固定标签。

## Docker 日志用内置 `stage.docker` 自动解析

教程另外给了个 Docker 场景的简化写法：

```alloy
discovery.docker "docker_containers" {
    host = "unix:///var/run/docker.sock"
}

discovery.relabel "docker_containers" {
    targets = discovery.docker.docker_containers.targets
    rule {
        source_labels = ["__meta_docker_container_name"]
        target_label  = "container"
    }
}

loki.source.docker "docker_logs" {
    host       = "unix:///var/run/docker.sock"
    targets    = discovery.relabel.docker_containers.output
    forward_to = [loki.process.process_logs.receiver]
}

loki.process "process_logs" {
    stage.docker { }
    forward_to = [loki.write.local_loki.receiver]
}

loki.write "local_loki" {
    endpoint {
        url = "http://localhost:3100/loki/api/v1/push"
    }
}
```

`stage.docker {}` 是一个开箱即用的预设 stage，专门用来解析 Docker 日志驱动（json-file/journald）产生的那层 JSON 包装（`{"log":"...", "stream":"stdout", "time":"..."}`），一步顶前面教程里手写的好几个 `stage.json`+`stage.timestamp`。**如果日志源本身就是 Docker 容器，优先用 `stage.docker {}`，不用照抄上面那套手写解析逻辑。**

**⚠️ 和 homelab 实际配置的写法差异**：这里 `discovery.relabel` 用的是 `targets = discovery.docker.docker_containers.targets`（真拿 target 列表去跑）+ 下游用 `.output`（relabel 之后的结果）；而 [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] 里 homelab 实际用的是 `targets = []`（留空，不实际跑）+ 下游 `loki.source.docker` 用 `relabel_rules = ....rules`（只要规则，由 `loki.source.docker` 自己内部套用）。**两种写法都对，是同一件事的两种实现方式**：一种是"提前把 relabel 做完，把结果传给下游"，另一种是"只传规则，让下游自己套用"。homelab 现在用的是后一种，看到官方教程写法不一样不用慌。

## 小结

`loki.process` 靠多个 `stage.*` 顺序执行、共享一张提取映射表：`stage.json`/`stage.regexp` 负责解析、`stage.timestamp` 改时间戳、`stage.drop`/`stage.match` 负责过滤、`stage.labels` 提升标签、`stage.output` 决定最终正文。Docker 场景有 `stage.docker {}` 这个现成预设，不用手写。

## 相关笔记

- [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] — homelab 实际部署的采集配置
- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — pipeline 的通用模式
