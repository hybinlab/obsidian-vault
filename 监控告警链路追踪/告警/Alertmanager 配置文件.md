---
publish: true
tags:
  - Alertmanager
  - 告警
  - 配置
---
来源：[Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)，按 v0.34.1 的 `docs/configuration.md` 原文整理（2026-10-02）。相关：[[Prometheus 配置文件]]。

## 概述

- Alertmanager 由**命令行参数**和**配置文件**共同配置：命令行参数配置不可变的系统参数；配置文件定义抑制规则、通知路由和接收器。
- 查看全部命令行参数：`alertmanager -h`。
- 路由树可以用官方 [可视化编辑器](https://www.prometheus.io/webtools/alerting/routing-tree-editor) 辅助构建。
- **热加载**：给进程发 `SIGHUP`，或 `POST /-/reload`。新配置格式不对时不生效，只记一条错误日志。

```bash
./alertmanager --config.file=alertmanager.yml
```

### 限制（Limits）

| 参数 | 作用 |
|---|---|
| `--silences.max-silences` | 静默（silence）最大数量，**包括已过期的** |
| `--silences.max-silence-size-bytes` | 单个静默的最大字节数 |

两者默认都不启用。

### 占位符

`[ ]` 表示可选；非列表参数的值为标注的默认值。

| 占位符 | 含义 |
|---|---|
| `<duration>` | 时长，如 `1d`、`1h30m`、`5m`、`10s`（支持 `y w d h m s ms`） |
| `<labelname>` | 匹配 `[a-zA-Z_][a-zA-Z0-9_]*` |
| `<labelvalue>` | unicode 字符串 |
| `<filepath>` | 当前工作目录下的有效路径 |
| `<secret>` | 密码等敏感字符串 |
| `<tmpl_string>` / `<tmpl_secret>` | 使用前会做模板展开的字符串 / 敏感字符串 |
| `<regex>` | RE2 正则，**两端自动锚定**；不想锚定就写 `.*<regex>.*` |

## 文件结构与 global

`global` 里的参数在其他所有配置段生效，并作为它们的默认值。

```yaml
global:
  # —— SMTP（邮件）——
  [ smtp_from: <tmpl_string> ]
  [ smtp_smarthost: <string> ]          # 含端口，如 smtp.example.org:587（25，或 587 走 STARTTLS）
  [ smtp_hello: <string> | default = "localhost" ]
  [ smtp_auth_username: <string> ]      # 为空则不认证；支持 CRAM-MD5、LOGIN、PLAIN（PLAIN 仅限 TLS）
  [ smtp_auth_password: <secret> ]      # LOGIN / PLAIN
  [ smtp_auth_password_file: <string> ]
  [ smtp_auth_identity: <string> ]      # PLAIN
  [ smtp_auth_secret: <secret> ]        # CRAM-MD5
  [ smtp_auth_secret_file: <string> ]
  [ smtp_require_tls: <bool> | default = true ]   # Go 不支持对远程 SMTP 走明文
  [ smtp_tls_config: <tls_config> ]
  [ smtp_force_implicit_tls: <bool> ]   # 无论端口都强制隐式 TLS

  # —— 各集成的默认值 ——
  [ jira_api_url: <string> ]
  [ slack_api_url: <secret> ] / [ slack_api_url_file: <filepath> ]
  [ slack_app_token: <secret> ] / [ slack_app_token_file: <filepath> ]
  [ slack_app_url: <string> ]
  [ victorops_api_key: <secret> ] / [ victorops_api_key_file: <filepath> ]   # 二者互斥
  [ victorops_api_url: <string> | default = "https://alert.victorops.com/integrations/generic/20131114/alert/" ]
  [ pagerduty_url: <string> | default = "https://events.pagerduty.com/v2/enqueue" ]
  [ opsgenie_api_key: <secret> ] / [ opsgenie_api_key_file: <filepath> ]
  [ opsgenie_api_url: <string> | default = "https://api.opsgenie.com/" ]
  [ rocketchat_api_url: <string> | default = "https://open.rocket.chat/" ]
  [ rocketchat_token(_file) / rocketchat_token_id(_file) ]                  # 各自与 _file 版互斥
  [ wechat_api_url: <string> | default = "https://qyapi.weixin.qq.com/cgi-bin/" ]
  [ wechat_api_secret: <secret> ] / [ wechat_api_secret_file: <string> ]
  [ wechat_api_corp_id: <string> ]
  [ telegram_api_url: <string> | default = "https://api.telegram.org" ]
  [ telegram_bot_token: <secret> ] / [ telegram_bot_token_file: <string> ]  # 互斥
  [ webex_api_url: <string> | default = "https://webexapis.com/v1/messages" ]
  [ mattermost_webhook_url: <secret> ] / [ mattermost_webhook_url_file: <string> ]

  # 默认 HTTP 客户端配置
  [ http_config: <http_config> ]

  # 告警没带 EndsAt 时，超过这个时间没更新就判定为已恢复。
  # 对 Prometheus 发来的告警无影响（它总会带 EndsAt）。
  [ resolve_timeout: <duration> | default = 5m ]

templates:                 # 自定义通知模板文件，最后一级可用通配符，如 'templates/*.tmpl'
  [ - <filepath> ... ]
route: <route>             # 路由树根节点
receivers:                 # 接收器列表
  - <receiver> ...
inhibit_rules:             # 抑制规则
  [ - <inhibit_rule> ... ]
mute_time_intervals:       # 已废弃，改用 time_intervals
  [ - <time_interval> ... ]
time_intervals:            # 用于静音 / 激活路由的时间段
  [ - <time_interval> ... ]
[ event_recorder: <event_recorder_config> ]   # 需 --enable-feature=event-recorder
[ tracing: <tracing_config> ]
```

## 路由 `<route>`

路由配置决定告警如何被**路由、聚合、限流、按时间静音**。

### 匹配流程

1. 所有告警从顶层路由进入，**顶层路由必须匹配所有告警**（不能配 matchers）。
2. 依次遍历子节点：
   - `continue: false`（默认）→ 命中第一个匹配的子节点就停止；
   - `continue: true` → 命中后继续匹配后面的兄弟节点。
3. 如果一个节点的子节点都不匹配（或没有子节点），就按**当前节点**的配置处理。

### 继承规则

| 参数 | 子路由未设置时 |
|---|---|
| `receiver`、`group_by`、`group_wait`、`group_interval`、`repeat_interval` | 继承父节点 |
| `labels` | 父→子**合并**，子可覆盖单个 label |
| `mute_time_intervals`、`active_time_intervals` | **不继承**：没写就是没有，不管父节点配了什么 |

> 最后一行在 v0.34.1 的原文里只写了「可选参数继承父节点」，「不继承」是 main 分支文档补充的说明。

### 字段

```yaml
[ receiver: <string> ]

# 分组依据的标签。如 cluster=A、alertname=LatencyHigh 的多条告警会合并成一组。
# 特殊值 ['...'] 表示按所有标签分组，等于完全不聚合——除非告警量很小
# 或下游通知系统自己会分组，否则一般不是你想要的。
[ group_by: '[' <labelname>, ... ']' ]

# 命中后是否继续匹配后面的兄弟节点
[ continue: <boolean> | default = false ]

match:      # 已废弃，改用 matchers（等值匹配）
match_re:   # 已废弃，改用 matchers（正则匹配）
matchers:
  [ - <matcher> ... ]

# 路由标签：通过模板函数 routeLabels（和 /api/v2/alerts/groups 的 routeLabels 字段）
# 提供给通知模板。父→子合并，子可覆盖。不影响分组。
# 值本身可以是模板，按告警组渲染；其中 .NotificationReason 总是 "unknown"，
# 依赖通知原因的内容请写在通知模板里。
labels:
  [ <labelname>: <tmpl_string>, ... ]

[ group_wait: <duration> | default = 30s ]
[ group_interval: <duration> | default = 5m ]
[ repeat_interval: <duration> | default = 4h ]

# 路由静音时间段：引用 time_intervals 里的 name。根节点不能配。
# 静音时不发通知，但其他行为照常（包括 continue 未设置时结束匹配）。
mute_time_intervals:
  [ - <string> ...]

# 路由激活时间段：只在这些时间段内发通知，空 = 一直激活。根节点不能配。
active_time_intervals:
  [ - <string> ...]

routes:
  [ - <route> ... ]
```

`labels` 示例（原文）：`description` 由子标签 `reason` 拼出，子路由只覆盖 `reason`，继承来的 `description` 自动生效。

```yaml
route:
  labels:
    reason: '{{ .GroupLabels.alertname }}'
    description: '{{ .GroupLabels.alertname }} firing ({{ routeLabels "reason" }})'
  routes:
    - matchers: [ service="database" ]
      group_by: [ alertname, database ]
      labels:
        reason: 'database {{ .GroupLabels.database }}'
```

### 三个时间参数

| 参数 | 默认 | 含义 |
|---|---|---|
| `group_wait` | 30s | 新告警组**首次**通知前等多久 |
| `group_interval` | 5m | 首次通知后，同组**有变化**时再次通知的间隔 |
| `repeat_interval` | 4h | 同组**无变化**时重复发送上一条通知的间隔 |

**group_wait**
- 用来等其他规则组 / 其他 Prometheus 的告警到齐，也等抑制告警到达，好在首次通知前把目标告警压掉。
- 太短：首次通知可能不完整，该被抑制的告警可能没被抑制（抑制告警还没到）。
- 太长：告警通知迟迟发不出去。
- 告警在 `group_wait` 结束前就恢复了 → **不发通知**，可减少抖动告警的噪音。
- 错过初始 `group_wait` 的告警，会在下一个 `group_interval` 发送。

**group_interval**
- `group_wait` 结束后立刻开始的**循环定时器**。每次到点检查：上个周期内有没有新告警触发或已有告警恢复，有就发通知；没有就转而检查 `repeat_interval` 是否到期。
- 它同时是每次发送通知的**上下文超时**：发送耗时超过 `group_interval` 会被取消。`group_interval` 很小、接收端又很慢时会遇到。

**repeat_interval**
- 上个 `group_interval` 内有新告警触发或告警恢复时，不会重复发送。
- 它在每个 `group_interval` 之后检查，所以应该是 `group_interval` 的**整数倍**，不是的话会向上取整到下一个整数倍。
- 如果比 `--data.retention` 还长，会改为在数据保留期结束时重复。

### 路由示例（原文）

```yaml
route:
  receiver: 'default-receiver'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  group_by: [cluster, alertname]
  # 没匹配下面任何子路由的告警，留在根节点，发给 default-receiver
  routes:
  # service=mysql 或 cassandra → database-pager
  - receiver: 'database-pager'
    group_wait: 10s
    matchers:
    - service=~"mysql|cassandra"
  # team=frontend → 按 product、environment 分组，而不是 cluster、alertname
  - receiver: 'frontend-pager'
    group_by: [product, environment]
    matchers:
    - team="frontend"
  # service=inhouse-service：非工作时间和节假日静音，命中后继续匹配下一个兄弟
  - receiver: 'dev-pager'
    matchers:
      - service="inhouse-service"
    mute_time_intervals:
      - offhours
      - holidays
    continue: true
  # 同样的告警：只在非工作时间和节假日激活 → 值班
  - receiver: 'on-call-pager'
    matchers:
      - service="inhouse-service"
    active_time_intervals:
      - offhours
      - holidays
```

## 时间段 `<time_interval>`

命名的时间段，在路由树里被引用，用来在特定时间静音 / 激活路由。

```yaml
name: <string>
time_intervals:
  - times:
    [ - <time_range> ...]
    weekdays:
    [ - <weekday_range> ...]
    days_of_month:
    [ - <days_of_month_range> ...]
    months:
    [ - <month_range> ...]
    years:
    [ - <year_range> ...]
    location: <string>
```

匹配规则：
- 每个字段都是列表，列表里**任一元素**满足即该字段匹配；不写的字段匹配任意值。
- 所有字段**都**匹配，该时刻才算落在时间段内。
- 没指定时区就按 **UTC**。

| 字段 | 写法 | 说明 |
|---|---|---|
| `times` | `start_time: HH:MM`、`end_time: HH:MM` | **左闭右开**，如 17:00–24:00 在 24:00 前一刻结束 |
| `weekdays` | `['monday:wednesday','saturday','sunday']` | 周日开始、周六结束；范围两端都包含；可跨周，如 `friday:monday` |
| `days_of_month` | `['1:5', '-3:-1']` | 从 1 开始；负数从月末倒数（1 月里 -1 = 31 日）；超出月份会被截断（2 月写 `1:31` 实际到 28/29）；两端包含 |
| `months` | `['1:3', 'may:august', 'december']` | 名称（不区分大小写）或数字，1 = 一月；两端包含 |
| `years` | `['2020:2022', '2030']` | 两端包含 |
| `location` | `'Asia/Shanghai'` | IANA 时区名；也可写 `'Local'`（Alertmanager 所在机器的本地时间）或 `'UTC'` |

Windows 上只支持 `Local` 和 `UTC`，除非通过 `ZONEINFO` 环境变量提供自定义时区库。

示例（原文用的悉尼时区，含义：当地时间周一到周五 9:00–17:00）：

```yaml
times:
- start_time: 09:00
  end_time: 17:00
weekdays: ['monday:friday']
```

## 抑制 `<inhibit_rule>`

当存在匹配 **source** 的告警时，把匹配 **target** 的告警静音。用来表达系统 / 服务间的依赖，故障时只发最相关的那几条告警。

- source 和 target 在 `equal` 列出的标签上**值必须相同**才生效。
- **缺失的标签等同于空值**：如果 `equal` 里的标签在 source 和 target 上都不存在，规则会生效。
- 防止自我抑制：同时匹配 target 和 source 两侧的告警，不会被同样两侧都匹配的告警（包括它自己）抑制。官方建议设计 matcher 时让告警**不会同时匹配两侧**，更好理解。

```yaml
name: <string>            # 可选；允许重名，但会影响按规则统计的指标

target_match:             # 已废弃，改用 target_matchers
target_match_re:          # 已废弃
target_matchers:          # 要被静音的告警需满足
  [ - <matcher> ... ]

source_match:             # 已废弃，改用 source_matchers
source_match_re:          # 已废弃
source_matchers:          # 至少存在一条满足这些条件的告警，抑制才生效
  [ - <matcher> ... ]

[ equal: '[' <labelname>, ... ']' ]
```

示例（个人补充，非原文）：同一实例有 critical 时，压掉 warning。

```yaml
inhibit_rules:
  - source_matchers: [ severity="critical" ]
    target_matchers: [ severity="warning" ]
    equal: [ alertname, instance ]
```

## 标签匹配器 `<matcher>`

匹配器用于路由、静音（silence）和抑制规则。

### 解析模式（UTF-8 过渡期）

Prometheus 正在支持标签和指标名使用 UTF-8。Alertmanager **0.27 起**换了新的 matcher 解析器，有一些不向后兼容的变化。过渡期内有三种模式：

| 模式 | 启用方式 | 行为 |
|---|---|---|
| fallback（**默认**） | 无需参数 | 先按 UTF-8 解析，不兼容再按 classic 解析并打 warn 日志（附修改建议） |
| UTF-8 strict | `--enable-feature="utf8-strict-mode"` | 禁用 classic matcher；有不兼容的 matcher 时**启动失败** |
| classic | `--enable-feature="classic-mode"` | 等同 0.26.0 及更早版本，怀疑新解析器有问题时用 |

- **新装**：建议直接开 UTF-8 strict 模式再写配置。
- **已有安装**：先在 fallback 模式跑，按 warn 日志改完配置，再开 strict。官方计划在后续两个版本内把 strict 设为默认。
- fallback 的 warn 示例：`foo=` 不兼容，建议改成 `foo=""`（UTF-8 matcher 右侧是必填项）。
- 偶尔两种解析器结果不一致（disagreement），这时用 classic 解析并打 warn。例如 `qux="\xf0\x9f\x99\x82"`：想匹配 🙂 表情就不用改；想匹配字面量 `\xf0...` 就改成 `qux="\\xf0\\x9f\\x99\\x82"`。

### 用 amtool 校验

不需要 Alertmanager 在运行。

```bash
amtool check-config config.yml                                        # 有 warn = 还不兼容 strict
amtool check-config config.yml --enable-feature="utf8-strict-mode"    # 直接按 strict 校验，失败会 FAILED
```

没有 warn、输出 `SUCCESS` 就说明兼容 UTF-8 strict 模式。

### UTF-8 matcher 语法

三个部分：

1. 标签名：不加引号的字面量，或双引号字符串。
2. 运算符：`=`、`!=`、`=~`（匹配正则）、`!~`（不匹配正则）。
3. 值 / 正则：不加引号的字面量，或双引号字符串。

- **不加引号的字面量**可以包含除保留字符外的所有 UTF-8 字符。保留字符：空白，以及 ``{ } ! = ~ , \ " ' ` ``。`foo`、`[a-zA-Z]+`、`Προμηθεύς` 合法，`foo!` 不合法。
- **双引号字符串**没有保留字符，但字面量双引号和反斜杠要用 `\` 转义（同 Go 字符串字面量规则）。例如匹配正则 `\d+` 要写成 `"\\d+"`。

### classic matcher 语法

- 标签名必须是合法的 Prometheus 标签名；运算符同上，含义同 PromQL 选择器。
- 值可以用双引号包起来，可以为空；里面按 OpenMetrics 转义：`\"`、`\n`、`\\`。

### YAML 引号 vs matcher 引号（易错）

`matchers:` 列表里的每一项是**一个完整的 YAML 字符串**，YAML 先处理，Alertmanager 再解析。YAML 的引号作用在整个 matcher 上，不会保护里面的单个部分。

| YAML 写法 | 何时用 | 例子 |
|---|---|---|
| 不加引号（plain） | matcher 里没有 YAML 特殊字符 `{ } [ ] , # \| > :` | `env !~ preprod` |
| 单引号 | 防住所有 YAML 特殊字符，里面可直接写双引号 | `'env =~ "prod\|staging"'` |
| 双引号 | 支持 YAML 转义，里面的双引号要写成 `\"` | `"env !~ \"uat\""` |

`env =~ "prod"` 不加外层引号也是合法 YAML，但内层双引号是给 Alertmanager 解析器用的，**防不住** YAML 特殊字符。值里可能有特殊字符时，一定要在 YAML 层把整个 matcher 括起来。

### 组合

多个 matcher **全部满足**才算匹配。`{alertname="Watchdog", severity=~"warning|critical"}` 匹配 `severity=critical`，不匹配 `severity=none`。

```yaml
# 1. YAML 列表
matchers:
  - alertname = Watchdog
  - severity =~ "warning|critical"

# 2. 短格式列表；值里有逗号等特殊字符时用双引号包住
matchers: [ foo = bar, dings != bums ]
matchers: [ "foo = \"bar,baz\"", "dings != bums" ]

# 3. 一个 PromQL 风格字符串，用单引号最省事
matchers: [ '{foo="bar", dings!="bums"}' ]

# 4. 用 YAML block 绕开转义问题
matchers:
  - |
      {quote=~"She said: \"Hi, all!( How're you…)?\""}
```

PromQL 风格字符串的规则：
- 允许末尾**一个**多余的逗号：`{a="1", b="2",}`。
- `{}` 可以省略，但必须**同时有或同时没有**，不能只写一边，也不能写成 `{{ }}`。
- 双引号外的空格、tab、换行都会被忽略。

## 接收器 `<receiver>`

一个接收器 = 一个名字 + 一个或多个通知集成。

```yaml
name: <string>             # 唯一
labels:                    # 用于查询和过滤
  [ <labelname>: <labelvalue>, ... ]

discord_configs / email_configs / mattermost_configs / msteams_configs /
msteamsv2_configs / jira_configs / opsgenie_configs / pagerduty_configs /
incidentio_configs / pushover_configs / rocketchat_configs / slack_configs /
sns_configs / telegram_configs / victorops_configs / webex_configs /
webhook_configs / wechat_configs:
  [ - <xxx_config>, ... ]
```

原文备注：新增的通知集成必须有一个有 push 权限的固定维护者。

### `<http_config>`（共享）

基于 HTTP 的接收器用的 HTTP 客户端配置。

```yaml
# basic_auth 和 authorization 互斥；oauth2 也不能与它们同时用
basic_auth:
  [ username: <string> ]
  [ password: <secret> ]            # 与 password_file 互斥
  [ password_file: <string> ]
authorization:
  [ type: <string> | default: Bearer ]
  [ credentials: <secret> ]         # 与 credentials_file 互斥
  [ credentials_file: <filename> ]
oauth2:
  [ <oauth2> ]

[ enable_http2: <bool> | default: true ]
[ proxy_url: <string> ]
[ no_proxy: <string> ]                         # 逗号分隔的 IP、CIDR、域名，可带端口
[ proxy_from_environment: <boolean> | default: false ]   # 读 HTTP(S)_PROXY / NO_PROXY
[ proxy_connect_header: [ <string>: [<secret>, ...] ] ]
[ follow_redirects: <bool> | default = true ]
tls_config:
  [ <tls_config> ]
http_headers:                       # 自定义请求头；程序自己设置的头不能被覆盖
  <header 名>:
    [ values: [<string>, ...] ]
    [ secrets: [<secret>, ...] ]    # 在配置页面里隐藏
    [ files: [<string>, ...] ]      # 从文件读
```

`<oauth2>`：client credentials 模式，用 `client_id`、`client_secret`（或 `client_secret_file`）去 `token_url` 取 token；还可以配 `scopes`、`endpoint_params`、`tls_config` 和代理参数（同上）。

`<tls_config>`：

```yaml
[ ca_file: <filepath> ]
[ cert_file: <filepath> ]
[ key_file: <filepath> ]
[ server_name: <string> ]
[ insecure_skip_verify: <boolean> | default = false ]
[ min_version: <string> ]    # TLS10 / TLS11 / TLS12 / TLS13，不设用 Go 默认 TLS12
[ max_version: <string> ]    # 不设用 Go 默认 TLS13
```

## 通知集成

原文给每种集成都列了完整字段。这里详记常用的四种，其余只列名字，用到时查原文。

| 集成 | `send_resolved` 默认 |
|---|---|
| email、wechat | **false** |
| webhook、telegram | true |

### `<email_config>`

```yaml
[ send_resolved: <boolean> | default = false ]
to: <tmpl_string>                 # 支持逗号分隔多个地址
[ from: <tmpl_string> | default = global.smtp_from ]
[ smarthost: <string> | default = global.smtp_smarthost ]
[ hello: <string> | default = global.smtp_hello ]
# 认证：各项默认取 global.smtp_auth_*；password 与 password_file 互斥，secret 与 secret_file 互斥
[ auth_username / auth_password / auth_password_file / auth_secret / auth_secret_file / auth_identity ]
[ require_tls: <bool> | default = global.smtp_require_tls ]
# true：任意端口都直接走 TLS；不设：按端口自动判断（465 隐式，其他显式）
[ force_implicit_tls: <bool> | default = nil ]
tls_config:
  [ <tls_config> | default = global.smtp_tls_config ]
[ html: <tmpl_string> | default = '{{ template "email.default.html" . }}' ]
[ text: <tmpl_string> ]
[ headers: { <string>: <tmpl_string>, ... } ]   # 会覆盖实现里已设置的头
threading:                        # 同一告警组的通知归到同一个邮件会话
  [ enabled: <boolean> | default = false ]
  [ thread_by_date: <string> | default = daily ]   # daily / none（none = 只按组 key）
```

```yaml
receivers:
  - name: email-implicit-tls
    email_configs:
      - to: alerts@example.com
        smarthost: smtp.example.com:8465
        force_implicit_tls: true          # 8465 端口也直接走 TLS
  - name: email-default
    email_configs:
      - to: alerts@example.com
        smarthost: smtp.example.com:465   # 自动识别为隐式 TLS
      - to: alerts@example.com
        smarthost: smtp.example.com:587   # 自动识别为显式 TLS（STARTTLS）
```

### `<webhook_config>`

通用接收器，对接没有内置集成的系统（钉钉、飞书一般走这个，通常要加一层转换服务或用 `payload`——个人补充）。

```yaml
[ send_resolved: <boolean> | default = true ]
url: <secret>                     # 与 url_file 互斥
url_file: <filepath>
[ http_config: <http_config> | default = global.http_config ]
[ max_alerts: <int> | default = 0 ]       # 单条消息最多带几条告警，0 = 不限，超出的截断
[ timeout: <duration> | default = 0s ]    # 0 = 不超时；大于 group_interval 时无效
# 用 Go 模板自定义 payload，结果必须是合法 JSON（可用 toJson）。
# Alertmanager 不校验结果，官方明确不对此提供支持，风险自负。
[ payload: { <string>: <tmpl_string>, ... } ]
```

默认 POST 的 JSON：

```
{
  "version": "4",
  "groupKey": <string>,            // 告警组的 key，可用于去重
  "truncatedAlerts": <int>,        // 因 max_alerts 被截断的数量
  "status": "<resolved|firing>",
  "receiver": <string>,
  "groupLabels": <object>,
  "commonLabels": <object>,
  "commonAnnotations": <object>,
  "externalURL": <string>,         // 回链到 Alertmanager
  "notification_reason": <string>, // 产生这条通知的原因
  "alerts": [
    {
      "status": "<resolved|firing>",
      "labels": <object>,
      "annotations": <object>,
      "startsAt": "<rfc3339>",
      "endsAt": "<rfc3339>",
      "generatorURL": <string>,    // 产生告警的来源
      "fingerprint": <string>      // 告警指纹
    }
  ]
}
```

现成的 webhook 对接见官方 [integrations 列表](https://prometheus.io/docs/operating/integrations/#alertmanager-webhook-receiver)；`payload` 用法示例见仓库 `examples/webhook/`（Gotify、MS Teams）。

### `<wechat_config>`（企业微信）

```yaml
[ send_resolved: <boolean> | default = false ]
[ api_secret: <secret> | default = global.wechat_api_secret ]   # 与 api_secret_file 二选一
[ api_secret_file: <string> | default = global.wechat_api_secret_file ]
[ api_url: <string> | default = global.wechat_api_url ]
[ corp_id: <string> | default = global.wechat_api_corp_id ]
[ message: <tmpl_string> | default = '{{ template "wechat.default.message" . }}' ]
[ message_type: <string> | default = 'text' ]    # text / markdown
[ agent_id: <string> | default = '{{ template "wechat.default.agent_id" . }}' ]
[ to_user: <string> | default = '{{ template "wechat.default.to_user" . }}' ]
[ to_party: <string> | default = '{{ template "wechat.default.to_party" . }}' ]
[ to_tag: <string> | default = '{{ template "wechat.default.to_tag" . }}' ]
```

### `<telegram_config>`

```yaml
[ send_resolved: <boolean> | default = true ]
[ api_url: <string> | default = global.telegram_api_url ]
[ bot_token: <secret> ]               # 与 bot_token_file 互斥
[ bot_token_file: <filepath> ]
[ chat_id: <int> ]                    # 与 chat_id_file 互斥
[ chat_id_file: <filepath> ]
[ message_thread_id: <int> ]          # 发到指定话题
[ message: <tmpl_string> default = '{{ template "telegram.default.message" .}}' ]
[ disable_notifications: <boolean> | default = false ]
# MarkdownV2 / Markdown / HTML / 空串（纯文本）。超过 Telegram 字数限制会被截断；HTML 模式下会换成兜底消息
[ parse_mode: <string> | default = "HTML" ]
[ http_config: <http_config> | default = global.http_config ]
```

### 其他集成

Discord、Mattermost、MS Teams（`msteams` / `msteamsv2`）、Jira、Opsgenie、PagerDuty、incident.io、Pushover、Rocket.Chat、Slack、AWS SNS、Splunk On-Call（VictorOps）、Webex。字段见原文对应的 `<xxx_config>` 小节。

## 链路追踪 `<tracing_config>`

```yaml
[ client_type: <string> | default = "grpc" ]    # http / grpc
[ endpoint: <string> | default = "" ]
[ sampling_fraction: <float> | default = 0.0 ]
[ insecure: <boolean> | default = false ]       # 禁用 TLS
[ tls_config: <tls_config> ]
[ http_headers: [ <http_header> ] ]
[ compression: <string> | default = "gzip" ]
[ timeout: <duration> | default = 0s ]
```

> v0.34.1 原文顶层结构里把这个 key 拼成了 `traciing`，是文档笔误，main 已改为 `tracing`。

## 事件记录器 `<event_recorder_config>`

- 记录 Alertmanager 的重要事件：进程启停、告警生命周期变化、创建静默、通知投递、静音 / 抑制导致的压制。
- 每个事件是结构化数据：时间戳、实例主机名、集群位置（开了 HA 时）和事件本身的数据。
- 需要 `--enable-feature=event-recorder` 才生效；没开的话事件被静默丢弃。
- 每个事件都会发到**所有**配置的输出。

```yaml
event_recorder:
  file_outputs:      # 每个事件写一行 JSON；目标文件被 rename/remove/create 时会重新打开（兼容 logrotate）
    [ - <file_output> ... ]
  webhook_outputs:
    [ - <webhook_output> ... ]
  kafka_outputs:
    [ - <kafka_output> ... ]
  stdout_outputs:
    [ - <stdout_output> ... ]
```

各输出的具体字段见原文。

## 个人补充（非原文）

- 改完配置先 `amtool check-config alertmanager.yml`，再 `curl -X POST http://<host>:9093/-/reload`。
- 典型的 group_by：`[alertname, cluster]` 或 `[alertname, instance]`。`['...']` 基本只在下游自己做分组时用。
- `time_intervals` 记得写 `location: 'Asia/Shanghai'`，否则按 UTC 算，「工作时间」会差 8 小时。
