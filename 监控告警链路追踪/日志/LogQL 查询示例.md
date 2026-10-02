---
publish: true
tags:
  - Loki
  - LogQL
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/query/query_examples/

相关：[[LogQL 日志查询]]、[[LogQL 指标查询]]、[[LogQL 模板函数]]、[[LogQL 查询最佳实践]]

## 一、日志查询

### 1. IP 过滤：排除地址范围

```logql
{job_name="myapp"} != ip("192.168.4.5-192.168.4.20")
```

返回**不在**该 IPv4 范围内的日志行。`ip()` 是行过滤器，直接对整行匹配。

### 2. IP 过滤：子网匹配并排除单个 IP

```logql
{job_name="myapp"}
	| logfmt
	| addr = ip("192.168.4.5/16")
	| addr != ip("192.168.4.2")
```

先用 `logfmt` 提取 `addr` 标签，再作为标签过滤器：匹配子网内的所有地址，排除某个具体 IP。

### 3. 安全：提取失败登录的用户和 IP（`/var/log/secure`）

```logql
{job="security"}
    |~ "Invalid user.*"
    | regexp "(^(?P<user>\\S+ {1,2}){8})"
    | regexp "(^(?P<ip>\\S+ {1,2}){10})"
    | line_format "IP = {{.ip}}\tUSER = {{.user}}"
```

用位置计数的正则取第 8 个字段为用户、第 10 个为 IP，再用 `line_format` 输出。**字段位置依赖具体日志格式**，换系统要调整数字。

### 4. 安全：成功登录记录

```logql
{job="security"}
    != "grafana_com"
    |= "session opened"
    != "sudo: "
    | regexp "(^(?P<user>\\S+ {1,2}){11})"
    | line_format "USER = {{.user}}"
```

先用多个行过滤器排除干扰项，再提取用户名。

## 二、过滤顺序（多阶段）

查询从左到右依次求值，建议顺序：**流选择器 → 行过滤器 → 解析器 → 标签过滤器**。

```logql
{cluster="ops-tools1", namespace="loki-dev", job="loki-dev/query-frontend"} |= "metrics.go" != "out of order" | logfmt | duration > 30s or status_code != "200"
```

1. 流选择器确定初始数据集
2. 两个行过滤器：含 `metrics.go` 且不含 `out of order`
3. `logfmt` 提取字段
4. 标签过滤器应用复合条件

## 三、多解析器与格式化

### 5. logfmt + regexp

原始日志：

```
level=debug ts=2020-10-02T10:10:42.092268913Z caller=logging.go:66 traceID=a9d4d8a928d8db1 msg="POST /api/prom/api/v1/query_range (200) 1.5s"
```

```logql
{job="loki-ops/query-frontend"} | logfmt | line_format "{{.msg}}" | regexp "(?P<method>\\w+) (?P<path>[\\w|/]+) \\((?P<status>\\d+?)\\) (?P<duration>.*)"
```

先用 `logfmt` 取出 `msg`，用 `line_format` 把 `msg` 变成日志行，再用 `regexp` 拆出 `method`、`path`、`status`、`duration`。**当一段日志里嵌套了另一种格式时，用"解析 → line_format → 再解析"的套路。**

### 6. 重排日志行用于阅读

```logql
{cluster="ops-tools1", name="querier", namespace="loki-dev"}
  |= "metrics.go" != "loki-canary"
  | logfmt
  | query != ""
  | label_format query="{{ Replace .query \"\\n\" \"\" -1 }}"
  | line_format "{{ .ts}}\t{{.duration}}\ttraceID = {{.traceID}}\t{{ printf \"%-100.100s\" .query }} "
```

- `label_format` 去掉 `query` 里的换行
- `line_format` 用 Tab 分隔，`printf "%-100.100s"` 把查询定宽 100 字符，输出成表格

输入（节选）：

```
level=info ts=2020-10-23T20:32:18.094668233Z caller=metrics.go:81 org_id=29 traceID=1980d41501b57b68 latency=fast query="{cluster=\"ops-tools1\", job=\"loki-ops/query-frontend\"} |= \"query_range\"" query_type=filter range_type=range length=15m0s step=7s duration=650.22401ms status=200 throughput_mb=1.529717 total_bytes_mb=0.994659
```

输出：

```
2020-10-23T20:32:18.094668233Z	650.22401ms	    traceID = 1980d41501b57b68	{cluster="ops-tools1", job="loki-ops/query-frontend"} |= "query_range"
```

### 7. 去除 ANSI 颜色码

```logql
{job="example"} | decolorize
```

`[2022-11-04 22:17:57.811] \033[0;32http\033[0m: GET /_health (0 ms) 204` → `[2022-11-04 22:17:57.811] http: GET /_health (0 ms) 204`，便于后续解析。

## 四、指标查询

### 8. 错误率（按主机）

```logql
sum by (host) (rate({job="mysql"}
    |= "error" != "timeout"
    | json
    | duration > 10s [1m]))
```

非超时错误、耗时超过 10s，按 `host` 汇总每秒速率。

### 9. 用 unwrap 算 p99 延迟

```logql
quantile_over_time(0.99,
  {cluster="ops-tools1",container="ingress-nginx"}
    | json
    | __error__ = ""
    | unwrap request_time [1m]) by (path)
```

按 `path` 分组求 `request_time` 的 99 分位。`| __error__ = ""` 过滤掉解析或转换失败的样本，避免污染结果。

### 10. 累加数值：按组织统计处理字节数

```logql
sum by (org_id) (
  sum_over_time(
  {cluster="ops-tools1",container="loki-dev"}
      |= "metrics.go"
      | logfmt
      | unwrap bytes_processed [1m])
  )
```

### 11. Top N：日志量最大的 10 个应用

```logql
topk(10,sum(rate({region="us-east1"}[5m])) by (name))
```

### 12. 按日志级别统计条数

```logql
sum(count_over_time({job="mysql"}[5m])) by (level)
```

### 13. 按区域统计 `/home` 的 GET 请求速率

```logql
avg(rate(({job="nginx"} |= "GET" | json | path="/home")[10s])) by (region)
```

## 面板中的用法（个人整理，待核实）

| 需求 | 参考示例 | 面板类型 |
|---|---|---|
| 各级别日志量趋势 | 12（`[$__auto]` 替换 `[5m]`） | Time series |
| 错误率、延迟分位数 | 8、9 | Time series |
| 日志量 Top N | 11（查询类型设为 Instant） | Bar gauge / Table |
| 失败登录明细 | 3 | Logs |

## 核对提示

- 示例 6 用了 `Replace .query "\n" "" -1`（首字母大写，参数顺序为 src、old、new、n），与 [[LogQL 模板函数]] 里的 `replace old new src` 不同。这是页面原样，应为旧写法，新版本请以模板函数页为准，并在你的 Loki 版本实测。
- 示例 13 把 `[10s]` 写在带括号的选择器和管道之后，写法不常见，我未验证，请实测；同时 10s 的区间对多数采集间隔过短。
- 示例 9 的 `__error__ = ""` 正好印证了 [[LogQL 指标查询]] 中我标注为"待核实"的用法，现已有官方示例支持。
- 示例 3、4 依赖 `/var/log/secure` 的具体字段位置，其他发行版需调整。
