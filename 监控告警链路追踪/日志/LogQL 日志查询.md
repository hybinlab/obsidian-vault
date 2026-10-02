---
publish: true
tags:
  - Loki
  - LogQL
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/query/log_queries/

## 结构

日志查询 = **流选择器** + 可选的**日志管道**。管道中的表达式**从左到右**依次执行，每个表达式可以过滤、解析或修改日志行和标签；某行被过滤掉后，后续表达式不再处理它。

```logql
{container="query-frontend",namespace="loki-dev"} |= "metrics.go" | logfmt | duration > 10s and throughput_mb < 500
```

## 1. 流选择器

花括号内用逗号分隔标签匹配器。

| 运算符 | 含义 |
|---|---|
| `=` / `!=` | 精确相等 / 不等 |
| `=~` / `!~` | 正则匹配 / 不匹配（**完全锚定**） |

```logql
{name =~ "mysql.+"}
{name !~ `mysql-\d+`}
```

- `.` 默认不匹配换行；需要时加 `(?s)`，或用 `[\S\s]`：`{name =~ "(?s).*mysql.*"}`。
- 含反斜杠的正则用反引号，免去转义。

## 2. 行过滤器（Line filter）

对日志内容做分布式 grep，被过滤的行不保留。

| 运算符 | 含义 |
|---|---|
| `\|=` | 包含字符串 |
| `!=` | 不包含字符串 |
| `\|~` | 正则匹配（**不锚定**，`.` 可匹配换行） |
| `!~` | 正则不匹配 |

```logql
{job="mysql"} |= "error"
{instance=~"kafka-[23]",name="kafka"} != "kafka.server:type=ReplicaManager"
{name="kafka"} |~ "tsdb-ops.*io:2003"
{name="cassandra"} |~ `error=\w+`
```

- **链式**：必须依次全部满足。`{job="mysql"} |= "error" != "timeout"`
- **忽略大小写**：正则前加 `(?i)`。`|~ "(?i)error"`
- **去除颜色码**：`{job="example"} | decolorize`
- 行过滤器尽量放在管道前部，速度最快。

## 3. 标签过滤器（Label filter）

对原有标签和解析器提取出的标签做过滤。

| 值类型 | 写法 | 运算符 |
|---|---|---|
| 字符串 | `"200"` 或 `` `us-central1` `` | `=` `!=` `=~` `!~` |
| Duration | `300ms`、`1.5h`、`2h45m`（单位 ns/us(µs)/ms/s/m/h） | `==`/`=` `!=` `>` `>=` `<` `<=` |
| 数值 | 64 位浮点，`250`、`89.923` | 同上 |
| Bytes | `42MB`、`1.5KiB`、`20B`（B/kB/MB/GB/TB/KB/KiB/MiB/GiB/TiB） | 同上 |

```logql
logfmt | duration > 1m and bytes_consumed > 20MB
```

**多个条件的连接**：`and`、`or`、逗号、空格、管道 `|`。其中逗号、空格、`|` 与 `and` 等价：

```logql
| duration >= 20ms or size == 20KB and method!~"2.."
| duration >= 20ms or size == 20KB | method!~"2.."
| duration >= 20ms or size == 20KB , method!~"2.."
| duration >= 20ms or size == 20KB  method!~"2.."
```

**优先级**：从左到右，没有 `and` 优先于 `or` 的规则。

```logql
| duration >= 20ms or method="GET" and size <= 20KB
# 等价于
| ((duration >= 20ms or method="GET") and size <= 20KB)

# 用括号改变优先级
| duration >= 20ms or (method="GET" and size <= 20KB)
```

**类型转换失败**：不会过滤该行，而是给该行加上 `__error__` 标签。

## 4. 解析器（Parser）

从日志内容中提取标签。

- **标签名规范化**：遵循 Prometheus 规则（字母、数字、下划线、冒号，不能数字开头）。`{ "a.b": {c: "d"}, e: "f" }` → `{a_b_c="d", e="f"}`。
- **重名**：提取出的标签与原标签冲突时，加 `_extracted` 后缀；可用 `label_format` 覆盖。

### json

**无参数**：提取全部属性。嵌套属性用 `_` 展平，**数组会被跳过**。

```logql
| json
```

输入：

```json
{
    "protocol": "HTTP/2.0",
    "servers": ["129.0.1.1","10.2.1.3"],
    "request": {
        "time": "6.032",
        "method": "GET",
        "host": "foo.grafana.net",
        "size": "55",
        "headers": { "Accept": "*/*", "User-Agent": "curl/7.68.0" }
    },
    "response": { "status": 401, "size": "228", "latency_seconds": "6.031" }
}
```

输出标签：

```
protocol=HTTP/2.0  request_time=6.032  request_method=GET  request_host=foo.grafana.net
request_size=55  request_headers_Accept=*/*  request_headers_User_Agent=curl/7.68.0
response_status=401  response_size=228  response_latency_seconds=6.031
```

**带参数**：只提取指定字段，支持字段访问、数组下标及组合。

```logql
| json first_server="servers[0]", ua="request.headers[\"User-Agent\"]"
# first_server=129.0.1.1, ua=curl/7.68.0
```

- 标签名与字段名相同时可简写：`| json servers` 等价于 `| json servers="servers"`。
- 取数组或对象时，返回其 JSON 字符串：

```logql
| json server_list="servers", headers="request.headers"
# server_list=["129.0.1.1","10.2.1.3"]
# headers={"Accept": "*/*", "User-Agent": "curl/7.68.0"}
```

### logfmt

```logql
| logfmt
| logfmt host, fwd_ip="fwd"
```

输入 `at=info method=GET path=/ host=grafana.net fwd="124.133.124.161" service=8ms status=200`，带参数时得到 `host=grafana.net`、`fwd_ip=124.133.124.161`。

标志位：

- `--strict`：遇到第一个格式错误的键值对就停止（默认宽容）。
- `--keep-empty`：保留只有键、没有值的项。

```logql
| logfmt --strict host, fwd_ip="fwd"
| logfmt --keep-empty --strict host
```

### pattern

用 `<name>` 捕获，`<_>` 表示跳过。比 regexp 简单、更快。

```logql
| pattern "<ip> - - <_> \"<method> <uri> <_>\" <status> <size> <_> \"<agent>\" <_>"
```

输入 NGINX 日志：

```
0.191.12.2 - - [10/Jun/2021:09:14:29 +0000] "GET /api/plugins/versioncheck HTTP/1.1" 200 2 "-" "Go-http-client/2.0" "13.76.247.102, 34.120.177.193" "TLSv1.2" "US" ""
```

得到 `ip=0.191.12.2`、`method=GET`、`uri=/api/plugins/versioncheck`、`status=200`、`size=2`、`agent=Go-http-client/2.0`。

- 表达式默认从行首锚定；若以字面量开头，前面要加 `<_>`：

```logql
| pattern "<_> msg=\"<method> <path> (<status>) <latency>\""
```

- 无效模式：没有命名捕获；两个未命名捕获之间没有分隔符。

### regexp

Go RE2 语法，必须使用**命名子匹配** `(?P<name>re)`。

```logql
| regexp "(?P<method>\\w+) (?P<path>[\\w|/]+) \\((?P<status>\\d+?)\\) (?P<duration>.*)"
```

输入 `POST /api/prom/api/v1/query_range (200) 1.5s` → `method=POST`、`path=/api/prom/api/v1/query_range`、`status=200`、`duration=1.5s`。

### unpack

解析由 `pack` 阶段（通常在采集端）打包的 JSON，把内嵌标签还原；特殊字段 `_entry` 会替换原日志行。

```logql
| unpack
| unpack | json     # 可与其他解析器串联
```

输入 `{"container":"myapp","pod":"pod-3223f","_entry":"original log message"}` → 标签 `container`、`pod`，日志行变为 `original log message`。

## 5. 格式化表达式

### line_format

用 Go text/template 重写日志行，标签作为变量注入。

```logql
{container="frontend"} | logfmt | line_format "{{.query}} {{.duration}}"
{container="frontend"} | logfmt | line_format "{{.ip}} {{.status}} {{div .duration 1000}}"
```

`ip=1.1.1.1`、`status=200`、`duration=3000` 时输出 `1.1.1.1 200 3`。

- 特殊函数：`__line__`（原日志行）、`__timestamp__`（时间戳）。
- 用反引号避免转义：``| line_format `{{.label_name}}` ``

### label_format

用逗号分隔多个操作，重命名、修改或新增标签。

```logql
| label_format dst=src                   # 重命名，src 被删除
| label_format dst="{{.status}} {{.query}}"   # 模板形式，源标签保留
```

- 目标标签不存在则新建。
- 模板函数与 `line_format` 相同，也支持 `__line__`、`__timestamp__`。
- 一个表达式只能对一个标签操作一次；同一标签多次操作需拆成多个表达式：`| label_format foo=bar | label_format foo="new"`。

## 6. 标签表达式

### drop

按名称或条件删除标签。

```logql
{job="varlogs"}|json|drop level, method="GET"
{job="varlogs"}|json|drop __error__
{job="varlogs"}|json|drop level, path, app=~"some-api.*"
```

- 第一条：无条件删除 `level`，`method` 仅在值为 `GET` 时删除。
- 第三条：`app` 匹配 `some-api.*` 的行才删除 `app` 标签，其他行保留。

### keep

只保留指定标签，其余全删。

```logql
{job="varlogs"}|json|keep level, method="GET"
{job="varlogs"}|json|keep level, tenant, app=~"some-api.*"
```

- 带条件的项：条件不满足时该标签不保留（`method="POST"` 的行只剩 `level`）。
- 不会删除 Loki 查询时加的 `error`、`error_details` 标签。

## 要点速记

1. 字符串用反引号，省去正则转义。
2. 流选择器的正则**完全锚定**，行过滤器的正则**不锚定**。
3. 解析或转换出错不会过滤行，而是加 `__error__` 标签，需要时用 `| __error__=""` 过滤或 `drop __error__` 清除。
4. 提取标签与原标签重名会加 `_extracted` 后缀。
5. 解析器可串联：`| unpack | json`。

## 待补充

- 抓取摘要里没有出现但官方页面可能有的内容：流选择器的"至少一个非空匹配器"规则、`|>` 模式匹配过滤、`ip()` 过滤、`distinct`、模板函数完整列表。
