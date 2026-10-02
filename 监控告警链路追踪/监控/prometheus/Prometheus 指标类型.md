---
publish: true
tags:
  - Prometheus
  - PromQL
---
指标类型决定了**能用哪些函数**，选错函数是写 PromQL 最常见的错误。相关：[[Prometheus 配置文件]]。

来源：[Understanding metric types](https://prometheus.io/docs/tutorials/understanding_metric_types/)（原文 Markdown：`prometheus/docs` 仓库 `docs/tutorials/understanding_metric_types.md`）。

## 速查

| 类型 | 变化方式 | 原文举例 | 原文提到的函数 |
|---|---|---|---|
| Counter | 只增，或重置 | 请求数、错误数 | `rate()` |
| Gauge | 可增可减 | 集群 Pod 数、队列中的事件数 | `max_over_time()`、`min_over_time()`、`avg_over_time()` |
| Histogram | 按桶累计计数 | 请求耗时（latency） | `histogram_quantile()`（配合 `rate()`） |
| Summary | 应用端计算 | 同样用于统计事件 | 原文未给函数 |

## 1. Counter（计数器）

只能增加或重置（reset），值不会比前一个值小。适合请求数、错误数等。

```promql
go_gc_duration_seconds_count                 # 原始值，一路向上
rate(go_gc_duration_seconds_count[5m])       # 每秒增长速度
```

- `rate()` 取一段时间窗口内的历史数据，计算**每秒**增长速度。
- 原文：**`rate()` 只适用于 Counter。**

## 2. Gauge（仪表盘）

可升可降的数值。适合集群里的 Pod 数、队列中的事件数等。

```promql
go_memstats_heap_alloc_bytes
```

原文只说 `max_over_time`、`min_over_time`、`avg_over_time` 可以用在 Gauge 上，没给具体查询。写法示例（我补的）：

```promql
avg_over_time(go_memstats_heap_alloc_bytes[5m])
```

## 3. Histogram（直方图）

比前两种复杂。用于**按桶计数**的数值，桶边界由开发者配置，典型例子是请求耗时（latency）。

不存每个请求的耗时，而是把它计入桶里。假设桶为 `le 0.3`、`le 0.5`、`le 0.7`、`le 1`、`le 1.2`（le = lower or equal），一个请求测出耗时后，**所有边界大于该值的桶**计数都 +1。

**请求 1**：`/ping` 耗时 0.25s

| 桶 | 计数 |
|---|---|
| 0 - 0.3 | 1 |
| 0 - 0.5 | 1 |
| 0 - 0.7 | 1 |
| 0 - 1 | 1 |
| 0 - 1.2 | 1 |
| 0 - +Inf | 1 |

- `+Inf` 桶默认自动添加。
- Histogram 是**累积频率**，所以比该值大的桶都会 +1。

**请求 2**：`/ping` 耗时 0.4s

| 桶 | 计数 |
|---|---|
| 0 - 0.3 | 1 |
| 0 - 0.5 | 2 |
| 0 - 0.7 | 2 |
| 0 - 1 | 2 |
| 0 - 1.2 | 2 |
| 0 - +Inf | 2 |

0.4 > 0.3，所以 `0.3` 桶不变，从 `0.5` 起都 +1。

### 在 Prometheus UI 里查

```promql
prometheus_http_request_duration_seconds_bucket{handler="/graph"}

# 用 histogram_quantile() 从直方图算分位数
histogram_quantile(0.9, prometheus_http_request_duration_seconds_bucket{handler="/graph"})

# 最近 5 分钟的分位数：加 rate() 和时间窗口
histogram_quantile(0.9, rate(prometheus_http_request_duration_seconds_bucket{handler="/graph"}[5m]))
```

原文截图里第二条查询的 90 分位是 0.09（秒）。

## 4. Summary（摘要）

- 同样用于统计事件，是 Histogram 的替代方案。
- **成本更低，但丢失的数据更多。**
- 在**应用层**计算，所以同一进程多个实例的指标**无法聚合**。
- 用于事先不知道桶边界的场景。
- 原文强烈建议：**能用 Histogram 就别用 Summary。**

## 个人补充

- 选型：只增不减 → Counter（配合 `rate`）；可增可减 → Gauge；要分位数 / 延迟分布 → Histogram，定不了桶才考虑 Summary。
- 直接看原始 Counter 意义不大，它只是累计值；`rate()` / `increase()` 会处理重启归零。
- Histogram 除 `_bucket` 外还暴露 `_sum`、`_count`；`_bucket` 本身是 Counter，所以生产里一般先 `rate()` 再 `histogram_quantile()`，且可以先 `sum by (le)` 跨实例聚合——这正是它比 Summary 好的地方。
- 和 Loki 对照：LogQL 的 `rate()`、`count_over_time()` 本质是把日志行当 Counter 算，语法与 PromQL 相近，见 [[LogQL 指标查询]]；`unwrap` 取数值时，延迟类用 `quantile_over_time`，累计类用 `sum_over_time`。
