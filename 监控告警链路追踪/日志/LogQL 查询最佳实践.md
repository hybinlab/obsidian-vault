---
publish: true
tags:
  - Loki
  - LogQL
  - 最佳实践
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/query/bp-query/

核心思路：Loki 只索引标签，所以**先用时间和标签缩小范围，再过滤内容，最后才解析**。

> 官方页面的原则共 5 条。下面每条的「差 / 好」示例是我按原则改写的，官方页面摘要里的示例不完整，已标注；未实测。

## 一条查询的推荐写法

```logql
{cluster="ops-tools1", namespace="loki-dev", job="loki-dev/query-frontend"}   # 1. 标签选择器，最具体
  |= "metrics.go" != "out of order"                                            # 2. 行过滤器，字符串匹配
  | logfmt                                                                     # 3. 解析器，只处理剩下的行
  | duration > 30s or status_code != "200"                                     # 4. 标签过滤器
```

（骨架取自官方查询示例，注释是我加的。）后面各条就是把这个顺序拆开讲。

## 1. 先缩小时间范围

Loki 每天生成一个索引文件，跨天查询要读取多个文件，范围越大越慢。

| | 做法 |
|---|---|
| 差 | 在 Grafana 里保持"最近 30 天"去查 `{job="app"} \|= "error"` |
| 好 | 时间选择器缩到出问题的那一小时 |
| API | `query_range` 带上 `start` 和 `end` 参数 |

```bash
curl -G "http://loki:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="app"} |= "error"' \
  --data-urlencode 'start=2024-05-01T10:00:00Z' \
  --data-urlencode 'end=2024-05-01T11:00:00Z'
```

## 2. 使用精确的标签选择器

选最具体的标签，减少扫描的日志量，查询也更短。

```logql
# 差：叠了宽泛的标签，范围反而更大或更啰嗦
{namespace="prod", app_name="carnivorousgreenhouse"}

# 好：一个能唯一定位应用的标签
{app_name="carnivorousgreenhouse"}
```

反例：只写 `{job=~".+"}` 或只用宽泛标签，会命中大量日志流。

## 3. 优先用简单行过滤，少用正则

`|=`、`!=` 比 `|~`、`!~` 求值更快。

```logql
# 差
{app_name="foo"} |~ "err.*r"
{app_name="foo"} |~ "error|ERROR"

# 好
{app_name="foo"} |= "error"
{app_name="foo"} |= "error" != "timeout"      # 链式过滤，每个都是简单字符串
```

必须用正则时：

- 忽略大小写：`|~ "(?i)error"`。
- 行过滤器里的正则**不锚定**，不用写 `.*` 开头和结尾。

## 4. 解析器放在行过滤之后

`json`、`logfmt`、`pattern`、`regexp`、`unpack` 开销大，先过滤再解析。

```logql
# 差：先解析全部日志，最后才过滤
{app_name="foo"} | json | level="error"

# 好：先用行过滤器丢掉大部分行，只解析剩下的
{app_name="foo"} |= "error" | json | level="error"
```

解析器的选择：能用 `pattern` 就不用 `regexp`，能用 `logfmt` / `json` 就不用 `regexp`（`pattern` 更简单，`regexp` 最重，见 [[LogQL 日志查询]]）。

## 5. 复杂查询用记录规则

查询很重、又反复用（面板、告警）时，用记录规则（recording rule）预先计算并保存结果，绕过即时查询的限制，读取更快。

```yaml
# ruler 规则文件（示意，语法与 Prometheus 规则相同）
groups:
  - name: api-errors
    rules:
      - record: app:api_error_rate:5m
        expr: |
          sum by (path) (
            rate({app="api"} |= "error" | logfmt [5m])
          )
```

面板里改为查询预计算后的指标，不再每次刷新都扫日志。规则文件的写法我按 Prometheus 规则格式推断，需对照 Loki 的 ruler 文档核实。

## 反例对照速查

| 场景 | 差 | 好 |
|---|---|---|
| 时间 | 30 天范围查一个小时的事 | 缩到问题时段 |
| 标签 | 只用宽泛标签 | 用最具体的标签 |
| 关键字 | `\|~ "err.*r"` | `\|= "error"` |
| 解析 | `\| json \| level="error"` | `\|= "error" \| json \| level="error"` |
| 重查询 | 面板每次直接算 | 记录规则预计算 |

## 核对提示

- 「每天一个索引文件」来自官方页面摘要，实际取决于 schema 的 index period 配置。
- 第 2、3 条的「差」示例是我构造的，官方页面摘要只给出了正向示例和文字描述。
- 「pattern 比 regexp 轻」是我的经验判断，不是这个页面的内容，未查证。
