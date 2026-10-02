---
publish: true
tags:
  - Loki
  - LogQL
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/query/template_functions/

模板函数用于 `line_format`（重写日志行）和 `label_format`（改写标签），语法是 Go text/template，详见 [[LogQL 日志查询]]。

**写法要点**
- 引用标签 `{{ .label }}`；内置变量 `__line__`（原始行）、`__timestamp__`（时间戳）。
- 管道 `|` 把上一步结果作为**下一个函数的最后一个参数**，所以参数顺序是「配置在前，被处理值在后」：`trimPrefix "/" .path` 等价于 `.path | trimPrefix "/"`。
- 整个模板用反引号包裹，免去转义。
- 标签值都是字符串，做数学运算前要 `int` / `float64`。

> 下文「输出」为按函数语义推演的结果，**未实测**；示例输入日志是我编的。函数签名和官方示例见文末速查表。

## 示例

### 1. 重排日志行，只看关心的字段

输入：`ts=2024-05-01T10:00:00Z method=GET path=/api/users status=200 duration=1.5s`

```logql
{app="api"} | logfmt | line_format `{{ .method }} {{ .path }} {{ .status }} {{ duration_seconds .duration }}s`
```

输出：`GET /api/users 200 1.5s`（`duration_seconds` 把 `1.5s` 转成数字 `1.5`）

### 2. 定宽对齐，输出成表格

```logql
{app="api"} | logfmt | line_format `{{ alignLeft 6 .method }} {{ alignRight 4 .status }}  {{ printf "%-20.20s" .path }}|`
```

输出：`GET     200  /api/users         |`
- `alignLeft 6` 补空格或截断到 6 字符；`printf "%-20.20s"` 左对齐并截断到 20 字符。

### 3. 截断超长日志行

```logql
{app="api"} |= "error" | line_format `{{ __line__ | trunc 80 }}`
```

只显示原始行的前 80 个字符，`trunc` 负数则取尾部。

### 4. 清理标签值：去前缀、去后缀、替换

| 目的 | 写法 | 输入 → 输出 |
|---|---|---|
| 去掉路径开头的 `/` | ``| label_format path=`{{ .path \| trimPrefix "/" }}` `` | `/api/users` → `api/users` |
| 去掉集群名后缀 | ``| label_format cluster=`{{ .cluster \| replace "-cluster" "" }}` `` | `prod-cluster` → `prod` |
| 统一大小写 | ``| label_format level=`{{ .level \| lower }}` `` | `ERROR` → `error` |

### 5. 空值兜底

```logql
{app="api"} | logfmt | line_format `user={{ default "-" .user }} path={{ .path }}`
```

`user` 为空时显示 `-`。

### 6. 条件判断

```logql
{app="api"} | logfmt | line_format `{{ if contains "Timeout" .err }}TIMEOUT{{ else }}{{ .err }}{{ end }}`
```

`err="ErrTimeout: dial tcp"` → `TIMEOUT`。可组合：`{{ if and (hasPrefix "Err" .err) (contains "Timeout" .err) }}...{{ end }}`。

### 7. 数值换算：字节转 MB

输入 `size=5242880`

```logql
{app="api"} | logfmt | line_format `{{ .path }} {{ divf (float64 .size) 1048576 }}MB`
```

输出：`/api/users 5MB`。整数除法用 `div (int .size) 1048576`（结果会取整）。

### 8. 耗时换算成毫秒

输入 `duration=1.5s`

```logql
{app="api"} | logfmt | line_format `{{ mulf (duration_seconds .duration) 1000 }}ms`
```

输出：`1500ms`

### 9. 正则替换：把路径里的 ID 归一化（控制标签基数）

输入 `path=/users/1234/orders/99`

```logql
{app="api"} | logfmt | label_format path=`{{ regexReplaceAll "[0-9]+" .path ":id" }}`
```

`path` 变成 `/users/:id/orders/:id`。`regexReplaceAll` 替换里可用 `${1}` 引用分组；不想展开 `$` 用 `regexReplaceAllLiteral`。

**用在指标查询里做按路径统计（Grafana 面板常用）：**

```logql
sum by (path) (
  count_over_time(
    {app="api"} | logfmt
      | label_format path=`{{ regexReplaceAll "[0-9]+" .path ":id" }}` [5m]
  )
)
```

不归一化的话每个 ID 都是一条序列，会撑爆序列数。

### 10. 解码：URL、Base64

```logql
{app="nginx"} | logfmt | line_format `{{ .q | urldecode }}`      # hello%20world → hello world
{app="api"}   | logfmt | line_format `{{ .token | b64dec }}`
```

### 11. 时间格式化

```logql
{app="api"} | line_format `{{ __timestamp__ | date "2006-01-02 15:04:05" }} {{ __line__ }}`
```

Go 时间布局用固定参考时间 `2006-01-02 15:04:05`，不能写 `YYYY-MM-DD`。

epoch 字段转日期（官方示例）：

```logql
... | json | line_format `from="{{date "2006-01-02" (unixToTime .from)}}"`
```

### 12. 统计出现次数

```logql
{app="api"} | line_format `{{ count "error" __line__ }}`
```

`count` 的第一个参数是**正则**，返回在该行里的匹配次数。

## 函数速查

### 时间

| 函数 | 说明 |
|---|---|
| `date fmt time` | 格式化时间 |
| `toDate fmt str` | 解析字符串，Loki 服务器本地时区 |
| `toDateInZone fmt zone str` | 在指定时区解析（Local、UTC 或 IANA 名称） |
| `now` | 当前时间（服务器本地时区） |
| `unixEpoch` / `unixEpochMillis` / `unixEpochNanos` | 时间 → Unix 秒 / 毫秒 / 纳秒 |
| `unixToTime epoch` | epoch 字符串 → 时间（支持天、秒、毫秒、微秒、纳秒） |
| `duration` / `duration_seconds` | `5m`、`24s30ms` → 秒；`duration` 是别名 |
| `bytes` | `5 MiB` 之类 → 字节数 |

### 字符串

| 函数 | 说明 |
|---|---|
| `lower` / `upper` / `title` | 大小写 |
| `trim` | 去两端空白 |
| `trimAll chars src` / `trimPrefix prefix src` / `trimSuffix suffix src` | 去指定字符 / 前缀 / 后缀 |
| `substr start end value` | 子串；start 为负取 `value[:end]`，end 为负取 `value[start:]` |
| `trunc count value` | 截断；负数从尾部取 |
| `replace old new src` | 简单替换 |
| `printf fmt args...` | Go 格式化 |
| `default d src` | src 为空时用 d |
| `repeat n value` | 重复 |
| `alignLeft n src` / `alignRight n src` | 定宽对齐 |
| `indent n src` / `nindent n src` | 每行缩进；`nindent` 开头加换行 |
| `b64enc` / `b64dec` | Base64 |
| `urlencode` / `urldecode` | URL 编码 |
| `fromJson v` | 解析 JSON 字符串，失败返回空 |

### 逻辑

| 函数 | 说明 |
|---|---|
| `contains s src` | src 是否包含 s |
| `hasPrefix prefix src` / `hasSuffix suffix src` | 前缀 / 后缀 |
| `eq a b` | 字符串相等 |

### 数学

| 函数 | 官方示例 → 输出 |
|---|---|
| `int` / `float64` | `{{ "3" \| int }}` → `3` |
| `add` / `addf` | `{{ add 3 2 5 }}` → `10`；`{{ addf 3.5 2 5 }}` → `10.5` |
| `sub` / `subf` | `{{ sub 5 2 }}` → `3`；`{{ subf 5.5 2 1.5 }}` → `2` |
| `mul` / `mulf` | `{{ mul 5 2 3 }}` → `30`；`{{ mulf 5.5 2 2.5 }}` → `27.5` |
| `div` / `divf` | `{{ div 10 2 }}` → `5`；`{{ divf 10 2 4 }}` → `1.25` |
| `mod` | `{{ mod 10 3 }}` → `1` |
| `floor` / `ceil` | `{{ floor 123.9999 }}`、`{{ ceil 123.001 }}` |
| `round a p [rOpt]` | `{{ round 123.555555 3 }}` → `123.556` |

### 正则

| 函数 | 说明 |
|---|---|
| `count regex src` | 统计匹配次数：`{{ count "a\|b" "abab" }}` → `4` |
| `regexReplaceAll regex src repl` | 正则替换，`$` 按 Expand 规则展开 |
| `regexReplaceAllLiteral regex src repl` | 正则替换，替换串按字面量 |

## 核对提示

- 抓取摘要里 `hasSuffix` 的示例写成 `hasSuffix .err "Timeout"`，与签名 `hasSuffix(suffix, src)` 的参数顺序相反，以签名为准。
- 官方页面里 `floor` / `ceil` 的输出写成 `123.0` / `124.0`，实际输出格式请实测。
- 模板逐行在查询时执行，数据量大时有开销，放在行过滤之后。
