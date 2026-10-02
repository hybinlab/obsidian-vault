---
publish: true
tags:
  - Loki
  - LogQL
cssclasses:
  - Loki
---

## 定位

LogQL 是 Loki 的查询语言，语法基于 PromQL，但不需要先掌握 PromQL。特点是**查询时推断结构（schema on read）**，不用预先定义日志字段。

来源：https://grafana.com/docs/loki/latest/query/

## 查询结构

```
{ log stream selector } | log pipeline
```

- **流选择器**：必填，先用标签定位日志流（Loki 只索引标签，所以这一步决定性能）。
- **日志管道**：可选，对选中的日志逐行过滤、解析、格式化。

## 两类查询

| 类型 | 返回 |
|---|---|
| 日志查询 | 日志行内容 |
| 指标查询 | 基于日志结果计算出的数值（可用于图表、告警） |

## Log Stream Selector

```logql
{service_name="nginx", status="500"}
```

| 运算符 | 含义 |
|---|---|
| `=` | 精确匹配 |
| `!=` | 不等于 |
| `=~` | 正则匹配 |
| `!~` | 正则不匹配 |

## Log Pipeline

管道由三类表达式组成，可串联。

### 1. 行过滤器（Line filter）

| 运算符 | 含义 |
|---|---|
| `\|=` | 包含字符串 |
| `!=` | 不包含字符串 |
| `\|~` | 正则匹配 |
| `!~` | 正则不匹配 |

### 2. 解析器（Parser）

把日志行解析成可用于过滤的标签，支持 `json`、`logfmt`、`pattern`、`regexp`、`unpack`。

### 3. 格式化表达式

- `line_format`：重写日志行
- `label_format`：改写或重命名标签

示例（解析 JSON 后重写日志行）：

```logql
{job=~"$job"} | json | line_format "➡️ {{.request_method}}"
```

## 待补充

概览页只给出骨架，以下内容在子页面，尚未整理：

- 日志查询：label filter 表达式、`drop` / `keep`、模板函数
- 指标查询：range vector、日志范围聚合、`unwrap`、聚合运算符与 `by` / `without`
- 各解析器的具体用法与性能差异
