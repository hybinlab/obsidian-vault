---
publish: true
tags:
  - Loki
  - 最佳实践
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/get-started/labels/bp-labels/

Loki 只索引标签，**每一种标签值组合就是一个独立的日志流（stream）**。标签设计得好不好，直接决定索引大小、chunk 大小和查询速度。相关：[[Loki 概述]]、[[LogQL 查询最佳实践]]。

## 一句话原则

**静态标签放心用，动态标签能不用就不用，用了也要值少且长期稳定。**

## 1. 静态标签是好的

值固定、数量有界的标签：region、cluster、server、application、namespace、environment。

```logql
{env="prod", app="nginx"}         # 某应用在某环境的全部日志
{env="prod", host="web-01"}       # 某台机器上所有应用的日志
```

静态标签可以承受较大的值集合：一个环境里有 1000 台主机是可以接受的。

## 2. 谨慎使用动态标签

动态标签（值随日志内容变化，如 `level`）会让流数量成倍增加，导致**索引变大、chunk 变小、性能下降**。

| 场景 | 差（用标签） | 好（用行过滤） |
|---|---|---|
| 只看 error | `{app="loki",level="error"}` | `{app="loki"} \|= "level=error"` |
| 排除 debug | `{app="loki",level!="debug"}` | `{app="loki"} != "level=debug"` |

- 官方说法：中低日志量的应用，用行过滤**同样快**。
- 差的写法会把日志拆成多个流（页面示例说拆成 5 个），排除类查询还要加载很多 chunk。
- 如果字段基数高、解析又耗性能，用 **structured metadata**（不进索引），不要做标签。

**数量参考**（页面明确说明针对**每天超过 10 TB 的超大租户**）：

- 活跃流：每租户 **< 100,000**
- 24 小时内的流总数：每租户 **< 100 万**
- 租户小 10 倍，标签数也应少 10 倍。

## 3. 必须用动态标签时

| 要求 | 好 | 坏 |
|---|---|---|
| 基数低，最好只有几十个值 | HTTP 路径段：`/load`、`/save`、`/update` | 用户 ID、请求 ID |
| 值长期存在 | 路由、服务名 | `trace_id`、`order_id` 等短命值 |
| 用户会经常查询 | 常用的筛选维度 | 没人查的标签（白白拖慢性能） |

## 4. 标签值必须有界

- 永远不要用无界（值会无限增长）的标签。
- 动态标签值：**个位数，最多几十个**。
- 静态标签可放宽，1000 个主机值可以。

## 5. 结合 chunk 大小考虑

- 本页写 `chunk_target_size` 设为 1MB（压缩后）约等于 5–10MB 未压缩日志。**注意**：[[Loki 配置最佳实践]] 页和 Loki 实际默认值都是 1.5MB（`1572864`，已实测），两个官方页面数值不一致，实际以 1.5MB 为准；下面 5MB 的判断阈值按比例理解即可。
- 如果一个流在 `max_chunk_age` 之内就产生了 5MB 日志，才值得考虑加动态标签来拆流；否则会造成 chunk 过早刷盘。
- 观察 chunk 刷盘原因的指标：

```promql
sum by (reason) (rate(loki_ingester_chunks_flushed_total{cluster="dev"}[1m]))
```

## 6. 排查客户端产生的高基数标签

采集端（Alloy、Fluentd、Fluent Bit、Docker 插件等）可能在你不知情时打出动态标签。用 Series API 或 `logcli --analyze-labels` 检查：

```bash
logcli series '{}' --analyze-labels      # 命令为我按页面提到的 flag 写出，参数细节需核实
```

页面里的输出示例：

```
Total Streams:  25017
Unique Labels:  8

Label Name     Unique Values    Found In Streams
requestId      24653            24979    ← 问题标签
logStream      1194             25016
logGroup       140              25016
accountId      13               25016
```

`requestId` 有 24,653 个不同的值，几乎每条日志一个流，**不应该作为标签**。

**修复**：去掉该标签，改用行过滤查询：

```logql
{logGroup="group1"} |= "requestId=32422355"
```

## 检查清单

1. 值是否有界？（动态标签个位数到几十个）
2. 值是否长期稳定？（不是 trace ID、订单号这类短命值）
3. 是否有人经常按它查询？
4. 能否用 `|= "level=error"` 代替 `level="error"`？
5. 采集端会不会偷偷加标签？用 `--analyze-labels` 检查。
