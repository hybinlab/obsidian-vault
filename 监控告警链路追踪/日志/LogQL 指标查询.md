---
publish: true
tags:
  - Loki
  - LogQL
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/query/metric_queries/

指标查询 = 对**日志查询的结果**套一个函数，把日志变成时间序列。这是 Grafana 面板（Time series、Stat、Bar gauge 等）的数据来源，日志查询（[[LogQL 日志查询]]）只能用在 Logs 面板里。

## 1. 日志范围聚合（Log range aggregation）

对每个日志流，在一个时间范围 `[range]` 内按**日志行**做计算。

| 函数 | 含义 |
|---|---|
| `rate(log-range)` | 每秒日志条数 |
| `count_over_time(log-range)` | 范围内每个流的日志条数 |
| `bytes_rate(log-range)` | 每个流每秒字节数 |
| `bytes_over_time(log-range)` | 范围内每个流的字节总量 |
| `absent_over_time(log-range)` | 范围内**有**数据返回空向量，**无**数据返回值为 1 的向量（用于告警"日志消失"） |

```logql
count_over_time({job="mysql"}[5m])
```

统计 5 分钟内 MySQL 的日志行数。

```logql
sum by (host) (rate({job="mysql"} |= "error" != "timeout" | json | duration > 10s [1m]))
```

带过滤器和解析器：非超时错误、耗时超过 10s 的日志，按 `host` 分组，求每秒速率。**`[1m]` 写在整个日志查询（含管道）之后。**

### offset 修饰符

必须紧跟在范围向量选择器之后：

```logql
count_over_time({job="mysql"}[5m] offset 5m)   # 正确
count_over_time({job="mysql"}[5m]) offset 5m   # 无效
```

## 2. 解包范围聚合（Unwrapped range aggregation）

不数日志行，而是把**提取出的标签值**当作样本值来算，例如统计耗时、字节数、状态码等数值。必须以 `unwrap` 结尾：

```
| unwrap label_identifier
```

### 类型转换

| 写法 | 作用 |
|---|---|
| `duration_seconds(label)`，简写 `duration(label)` | 把 Go 时间格式（`5m`、`24s30ms`）转成秒 |
| `bytes(label)` | 把字节单位（`5 MiB`、`3k`、`1G`）转成字节数 |

转换失败时，该样本被打上 `__error__` 标签。

### 函数

| 函数 | 含义 |
|---|---|
| `rate(unwrapped-range)` | 范围内所有值之和的每秒速率 |
| `rate_counter(unwrapped-range)` | 把值当作计数器，算每秒速率 |
| `sum_over_time` | 求和 |
| `avg_over_time` | 平均值 |
| `max_over_time` / `min_over_time` | 最大 / 最小 |
| `first_over_time` / `last_over_time` | 第一个 / 最后一个值 |
| `stdvar_over_time` / `stddev_over_time` | 总体方差 / 标准差 |
| `quantile_over_time(φ, range)` | φ 分位数，0 ≤ φ ≤ 1 |
| `absent_over_time` | 同上 |

### 分组语法

```
<aggr-op>([parameter,] <unwrapped-range>) [without|by (<label list>)]
```

- `without` 移除列出的标签，`by` 仅保留列出的标签。
- 摘要称：除 `sum_over_time`、`absent_over_time`、`rate`、`rate_counter` 外，其余函数都支持这种分组。

示例（我按语法写的，非官方原文；假设日志用 logfmt，含 `duration` 字段）：

```logql
quantile_over_time(0.95,
  {app="api"} | logfmt | unwrap duration(duration) [5m]
) by (route)
```

## 3. 内置聚合运算符

与 Prometheus 兼容，作用于向量表达式。

| 运算符 | 含义 |
|---|---|
| `sum` `avg` `min` `max` | 基本统计 |
| `stddev` `stdvar` | 标准差 / 方差 |
| `count` | 元素个数 |
| `topk` `bottomk` | 取最大 / 最小的 k 个，**保留原始标签** |
| `sort` `sort_desc` | 升序 / 降序排序 |

```
<aggr-op>([parameter,] <vector expression>) [without|by (<label list>)]
```

## 4. 其他函数

`vector(s)`：把标量转成无标签向量，用来避免"无数据时面板显示 No data"：

```logql
sum(count_over_time({namespace="traefik"}[5m])) or vector(0)
```

## 5. 概率聚合：approx_topk

`topk` 的近似版，用于原始查询超时或超过最大序列数限制时。

```logql
approx_topk(k, <vector expression>)
```

- 仅支持**即时查询**。
- 不支持分组，需在内层用 `sum by` / `sum without`。
- 基于分片的 Count-Min Sketch；k 接近堆大小（默认 10,000）时精度下降。

## 6. 结果排序

指标查询结果**顺序不保证**，除非用 `sort` / `sort_desc`。它们只对**即时查询**有效，范围查询的顺序未定义。

## 面板编写要点（个人整理，非页面原文，待核实）

- 写 Time series 面板：`sum by (label) (rate({...}[$__auto]))` 或 `count_over_time({...}[$__auto])`，`$__auto` 由 Grafana 按面板宽度和时间范围自动选择区间；也可用 `$__interval`、`$__range`。
- 面板变量常写成 `{job=~"$job"}`（多选变量需用 `=~`）。
- 无数据时用 `or vector(0)` 补零。
- Stat / Bar gauge 的 Top N 用 `topk(N, sum by (x) (count_over_time(...[$__range])))`，并把查询类型设为 Instant。

