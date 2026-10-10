---
publish: true
tags:
  - Grafana
  - 模板变量
  - Dashboard
---
来源：[Prometheus Book - Grafana 模板化 Dashboard](https://yunlzheng.gitbook.io/prometheus-book/part-ii-prometheus-jin-jie/grafana/templating)

## 核心概念

模板变量让 Dashboard 变「动态」——不用硬编码值，通过下拉菜单切换，PromQL 表达式自动替换变量。

变量定义：`Dashboard Settings → Variables`，引用方式 `$variable_name`。

## 五种变量类型

| 类型 | 用途 |
|---|---|
| **Query** | 从数据源动态查询值 |
| **Interval** | 时间范围（如 `$__rate_interval`） |
| **Datasource** | 切换数据源 |
| **Custom** | 手动定义值列表 |
| **Constant** | 导入时配置常量 |

## Query 变量核心函数

与 Prometheus 配合使用：

| 函数 | 说明 |
|---|---|
| `label_values(label)` | 从所有指标提取指定标签的值 |
| `label_values(metric, label)` | 从特定指标提取标签值 |
| `metrics(metric)` | 返回匹配指标名列表 |
| `query_result(query)` | 返回查询结果 |

### 示例

```promql
# 提取 nodejob 的所有实例
label_values(up{job="node"}, instance)

# 等价写法，先过滤 job 再取值
label_values(up, instance)
```

## 动态面板 / 行

启用 **Multi-value** 后，配合 **Repeat** 选项可以自动生成面板或行：

- `Repeat → variable`（选择变量名）
- 每个变量值生成一个面板/行
- 常用于按实例、job 分组展示

## 常用内置变量

| 变量 | 说明 |
|---|---|
| `$__interval` | 查询时间间隔 |
| `$__rate_interval` | rate() 推荐时间窗口（通常是 interval×2） |
| `$__range` | 选定时间范围 |
| `$job` | 当前选中的 job |
| `$instance` | 当前选中的 instance |

## 实际用法

Dashboard 顶部放一个 `node` 变量（Query: `label_values(up, job)`），面板里写：

```promql
rate(node_cpu_seconds_total{job=~"$node"}[$__rate_interval])
```

切换下拉框，所有面板同步刷新。

配合 `__rate_interval` 是最佳实践，能确保 rate 计算的时间窗口始终合理。
