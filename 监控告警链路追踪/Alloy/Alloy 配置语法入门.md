---
publish: true
---

承接 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里提到的 Component/Pipeline 概念，这里整理配置语言本身的三个基础元素：**Block、Attribute、Expression**，并配上官方文档里的实际例子。

## Block（块）与 Attribute（属性）

- **Attribute**：`NAME = VALUE` 形式，设置单个值
- **Block**：用花括号 `{}` 组织的一组相关配置，结构固定为「块名（必须）+ 可选的用户自定义 label + 内部的属性/嵌套块」
- 声明式语法：只描述"要什么"，解析器自动处理依赖关系，**书写顺序不影响执行**
- 支持 `//` 单行注释、`/* */` 多行块注释；空行、多余空格都会被忽略，`alloy fmt` 负责统一格式

无标签块（顶层配置类，只有一个实例，不需要区分）：

```alloy
BLOCK_NAME {
  IDENTIFIER = EXPRESSION   // 属性

  NESTED_BLOCK_NAME {
    // 嵌套块内容
  }
}
```

有标签块（组件类，同类型可以起多个实例，靠 label 区分）：

```alloy
// 组件名 "local.file"，label "api_key"
local.file "api_key" {
  filename  = sys.env("API_KEY_PATH")
  is_secret = true
}

// 组件名 "prometheus.scrape"，label "web_servers"
prometheus.scrape "web_servers" {
  targets      = discovery.kubernetes.services.targets
  metrics_path = "/metrics"
}
```

顶层属性 + 组件块 + 嵌套块混用的完整例子：

```alloy
// 顶层属性，控制 Alloy 自身的日志级别
log_level = "debug"

prometheus.scrape "app" {
  targets         = [{ "__address__" = "localhost:9090" }]
  scrape_interval = "15s"

  // 嵌套块
  basic_auth {
    username = "admin"
    password = sys.env("ADMIN_PASSWORD")
  }
}
```

多行表达式和格式容忍度（换行/空行不影响解析）：

```alloy
targets = [
  { "__address__" = "server1:9090" },
  { "__address__" = "server2:9090" },
  { "__address__" = "server3:9090" }
]
```

## Component（组件）

组件是最小执行单元，一个组件只干一件事。命名前缀表明所属类别：

| 前缀 | 含义 | 示例 |
| --- | --- | --- |
| `local.*` | 本地资源读取 | `local.file` 读取磁盘文件内容 |
| `prometheus.*` | Prometheus 生态 | `prometheus.scrape` 抓指标、`prometheus.remote_write` 发指标 |
| `loki.*` | Loki 生态 | `loki.write` 发日志 |
| `discovery.*` | 服务发现 | `discovery.kubernetes` 发现 K8s 服务 |

组件有两类接口：

- **Arguments（输入）**：配置组件行为的属性/嵌套块
- **Exports（输出）**：组件对外暴露的值，会随时间变化（比如文件内容更新）

**同一组件类型开多个实例**（label 不同，各自独立抓取，转发到同一个下游）：

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

**跨组件引用导出值**，串成一条 pipeline（`local.file` 读密钥文件 → 作为 `prometheus.remote_write` 的认证密码），上游文件内容变化时下游会自动重新求值：

```alloy
local.file "api_key" {
  filename = "/etc/secrets/api.key"
}

prometheus.remote_write "production" {
  endpoint {
    url = "https://prometheus.example.com/api/v1/write"

    basic_auth {
      username = "metrics"
      password = local.file.api_key.content   // 引用上面组件的导出值
    }
  }
}
```

**多层嵌套块**（`endpoint` 里套 `basic_auth`，同级还有 `queue_config` 控制发送队列参数）：

```alloy
prometheus.remote_write "production" {
  endpoint {
    url = "https://prometheus.example.com/api/v1/write"

    basic_auth {
      username = "metrics"
      password = local.file.credentials.content
    }
  }

  queue_config {
    capacity              = 10000
    max_samples_per_send  = 2000
  }
}
```

## Expression（表达式）

Attribute 的值除了写常量，还可以写表达式，支持四种形式：

| 形式 | 例子 |
| --- | --- |
| 字面值 | `"debug"`、`8080`、`true` |
| 组件引用 | `local.file.config.content` |
| 函数调用 | `sys.env("HOME")`、`encoding.from_json(local.file.data.content)` |
| 算术/逻辑运算 | `1 + 2`、`port_base + offset` |

实际配置里常见的组合用法：用 `sys.env()` 从环境变量取密码，避免明文写进配置文件：

```alloy
prometheus.scrape "app" {
  targets = [{ "__address__" = "localhost:9090" }]

  basic_auth {
    username = "admin"
    password = sys.env("ADMIN_PASSWORD")   // 函数调用，运行时从环境变量取值
  }
}
```

表达式在组件启动时求值一次，之后**依赖项变化会触发重新求值**（比如上面例子里 `local.file.api_key.content` 对应的文件被改写，下游 `prometheus.remote_write` 会自动拿到新密码，不用重启）；赋值前有类型检查，类型不对直接报配置错误，不会等到运行时才炸。

## 小结

三者的关系：Block/Attribute 是配置的骨架，Component 是功能单元（用 Block 声明，靠 label 区分多实例），Expression 是让配置动态起来的胶水（把一个组件的 Exports 接到另一个组件的 Arguments 上，或者用函数从环境变量/文件里取值）。写 Alloy 配置本质就是拿这三样东西拼 pipeline。

## 相关资源

- 官方 Tutorials（逐步搭建完整采集 pipeline）
- 标准库函数参考（`sys.env`、`encoding.from_json` 等内置函数全集）
- CLI `alloy fmt`（格式化工具）
