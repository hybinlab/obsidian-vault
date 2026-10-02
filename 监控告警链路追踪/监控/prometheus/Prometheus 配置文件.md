---
publish: true
tags:
  - Prometheus
  - 配置
---
安装部分略。实际部署见 [[Prometheus + Grafana 部署文档]]。

## 最小配置

```yaml
global:
  scrape_interval:     15s
  evaluation_interval: 15s

rule_files:
  # - "first.rules"
  # - "second.rules"

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']
```

这份配置让 Prometheus 抓取自己的 `localhost:9090/metrics`。

| 块                        | 作用                        |
| ------------------------ | ------------------------- |
| `global`                 | 全局默认值                     |
| `rule_files`             | 记录规则、告警规则文件的位置            |
| `scrape_configs`         | 抓取什么：一个 `job_name` 对应一组目标 |
| `static_configs.targets` | 目标地址，默认请求 `/metrics`      |

`scrape_interval` 控制抓取频率，可在单个 job 里覆盖；`evaluation_interval` 控制规则评估频率，规则用于生成新序列和告警。

## 启动与热加载

```bash
./prometheus --config.file=prometheus.yml
```

启动后访问 `http://localhost:9090`，表达式浏览器在 `/query`。

改完配置不必重启，两种方式（会重新加载规则文件和抓取配置，**配置有误会被拒绝并记入日志，旧配置继续生效**）：

```bash
kill -HUP <pid>
curl -X POST http://localhost:9090/-/reload      # 需要启动参数 --web.enable-lifecycle
```

## 顶层配置块

`global`、`scrape_configs`、`rule_files`、`alerting`（对接 Alertmanager）、`remote_write`、`remote_read`、`storage`（TSDB 与 exemplar 调优）、`tracing`。

日常主要用前四个。

## global 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `scrape_interval` | 1m | 默认抓取间隔 |
| `scrape_timeout` | 10s | 单次抓取超时 |
| `evaluation_interval` | 1m | 规则评估间隔 |
| `rule_query_offset` | 0s | 规则评估时的时间戳偏移，用于等待指标就绪 |
| `external_labels` | 无 | 发往外部系统（联邦、remote write、告警）时附加的标签；值里的 `${var}` / `$var` 在启动时展开为环境变量 |
| `query_log_file` | 无 | PromQL 查询日志文件 |
| `scrape_failure_log_file` | 无 | 抓取失败日志文件 |
| `body_size_limit` | 0（不限） | 单次响应未压缩体积上限 |
| `sample_limit` | 0（不限） | 单次抓取样本数上限 |
| `label_limit` | 0（不限） | 单个样本标签数上限 |
| `scrape_native_histograms` | false | 是否摄取 native histogram |

注意：页面的默认值是 `1m`，但最小示例和多数教程写的是 `15s`，那是示例里**显式写出**的，不是默认值。

## scrape_config 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `job_name` | 必填 | 在所有 scrape_config 中唯一 |
| `scrape_interval` | 继承 global | 本 job 的覆盖值 |
| `scrape_timeout` | 继承 global | 不能超过 `scrape_interval` |
| `metrics_path` | `/metrics` | 指标路径 |
| `scheme` | `http` | `http` 或 `https` |
| `params` | 无 | 附加 URL 参数 |
| `honor_labels` | false | 抓取到的标签与服务端标签冲突时是否保留抓取到的 |
| `honor_timestamps` | true | 是否采用目标暴露的时间戳 |
| `sample_limit` / `label_limit` | 0 | job 级限制 |

### 目标来源

- 静态：`static_configs`
- 文件发现：`file_sd_configs`
- 云与平台：`consul_sd_configs`、`kubernetes_sd_configs`、`aws_sd_configs`、`azure_sd_configs`、`docker_sd_configs`，页面称另有 20 多种

文件发现的好处是**目标变动自动生效，无需重启或 reload**：

```yaml
scrape_configs:
  - job_name: api
    file_sd_configs:
      - files: ['targets/*.json']     # 这一行是我写的示意，字段以官方为准
```

```json
[
  {
    "targets": ["host1:9090", "host2:9090"],
    "labels": {"job": "api-server"}
  }
]
```

### 认证与 TLS

HTTP 类配置支持 basic auth（`username` + `password`）、`authorization`（Bearer 或自定义类型）、OAuth 2.0（`client_id`、`token_url`、scopes）和 TLS（CA、客户端证书和密钥、`insecure_skip_verify`）。

## Relabel

`relabel_configs`（抓取**前**，作用于目标）和 `metric_relabel_configs`（抓取**后**，作用于样本）用来改写标签或过滤。

字段：

| 字段 | 说明 |
|---|---|
| `source_labels` | 输入标签列表 |
| `regex` | 匹配模式，默认 `.*` |
| `target_label` | 输出标签名 |
| `replacement` | 替换内容，可用 `$1`、`$2` 引用捕获组 |
| `action` | 见下 |

| action | 作用 |
|---|---|
| `keep` / `drop` | 按标签正则保留 / 丢弃目标 |
| `replace` | 改写标签值 |
| `labelmap` | 批量改写标签名 |
| `labeldrop` / `labelkeep` | 按标签名删除 / 保留 |
| `hashmod` | 哈希取模，用于分片 |

示例：

```yaml
scrape_configs:
  - job_name: node
    static_configs:
      - targets: ['10.0.0.1:9100']
    relabel_configs:
      - source_labels: [__address__]
        regex: '(.*):\d+'
        target_label: host
        replacement: '$1'
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'go_.*'
        action: drop
```

第一段把 `10.0.0.1:9100` 取出 IP 写入 `host` 标签；第二段丢弃所有 `go_` 开头的指标，减少序列数。

## 约定

- **duration**：`1d`、`1h30m`、`5m`、`10s`，单位 y、w、d、h、m、s、ms。
- **size**：B、KB、MB、GB、TB、PB、EB。
- **labelname**：`[a-zA-Z_][a-zA-Z0-9_]*`。

## 表达式浏览器里的示例

```promql
promhttp_metric_handler_requests_total                       # 全部序列
promhttp_metric_handler_requests_total{code="200"}           # 按标签过滤
count(promhttp_metric_handler_requests_total)                # 计数
rate(promhttp_metric_handler_requests_total{code="200"}[1m]) # 画图
```

## 对照homelab的配置

[[Prometheus + Grafana 部署文档]] 里用了 `scrape_interval: 15s`、`evaluation_interval: 15s`，启动参数 `--config.file`、`--storage.tsdb.path`、`--storage.tsdb.retention.time=30d`。后两个是启动参数，**不在 `prometheus.yml` 里**，页面摘要也没有提到它们，我没有在官方页面确认它们的写法，请你对照 `prometheus --help`。

## 核对提示

- 内容基于 WebFetch 摘要，不是页面原文；`remote_write`、`storage`、`tracing`、`alerting` 块的字段没有展开，需要时再单独整理。
- 官方 `first_steps` 页面本身只有一个最小示例，上面的参数表主要来自第二个页面。
- `file_sd_configs` 的 `files` 字段和 relabel 示例是我写的，不是官方原文。
- 参数默认值（如 `scrape_interval` 1m）以你使用版本的官方文档为准。
