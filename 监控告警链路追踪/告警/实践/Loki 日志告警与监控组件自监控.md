---
publish: true
tags:
  - Loki
  - Prometheus
  - Alertmanager
  - 告警
  - homelab
---
> 日期：2026-10-07
> 背景：日志早已经由 Alloy 采集进 Loki，但没有任何日志告警（Loki ruler 未配置，Grafana 里也没有告警规则），出问题只能事后查；Loki / Alloy / Grafana / Prometheus 自身也没有被监控。本次把日志告警接进现有的 [[Prometheus 告警 → ntfy 手机推送]] 链路，并补上监控组件自监控。
> 顺带：middleware（192.168.31.6）的抓取目标一直 down，先注释掉（后来查明 node_exporter 根本没装过，已改装 Alloy）。
> 2026-10-07 晚更新：bastion、middleware 改用 Alloy 采集指标和日志（见 [[Ansible 批量部署 Alloy 实战记录]]），LogIngestionStopped 覆盖 4 台机器；新增 FrpcReconnecting。
> 2026-10-15 运行核验快照：docker-host 上 Prometheus 9/9 targets 为 `up`，5 个规则组共 29 条规则均为 `health=ok`；Loki `log-alerts` 组的 6 条规则已加载且 `health=ok`。Alloy `/-/ready` 返回 HTTP 200。快照中 Loki 关闭认证、日志保留 30 天、ruler 每分钟评估并将告警送往 `http://alertmanager:9093`；当时 Alertmanager 默认路由到 ntfy，Watchdog 路由到 `null`。
> 2026-10-15 用户确认：frpc 标签/告警偏差、外部 dead-man、备用通知通道、PVE SMART 检查，以及 PVE/OpenWrt/ECS/database 监控相关事项均已完成。下文保留初次部署步骤和历史核验记录；部署时以当前配置为准。

---

## 架构

```
syslog / auth.log / 容器日志
   ↓ Alloy（docker-host、agent）
Loki :3100 ── ruler 每分钟执行 LogQL 规则（loki-rules/*.yml）
   ↓ 告警
Alertmanager :9093  ←── Prometheus（rules/*.yml，含新加的 monitoring-stack）
   ↓ webhook ?template=am
ntfy → 手机
```

日志告警和指标告警走**同一个 Alertmanager、同一个 ntfy 模板**，手机上看起来没有区别。

### 本次改动的文件（docker-host `/root/monitoring/`）

| 文件 | 改动 |
|---|---|
| `loki-config.yaml` | 新增 `ruler:` 块 |
| `loki-rules/log-alerts.yml` | 新建，6 条日志告警 |
| `docker-compose.yml` | loki 挂载 `./loki-rules:/loki/rules/fake:ro` |
| `prometheus.yml` | 新增 prometheus / loki / alloy / grafana 抓取；注释 middleware |
| `rules/monitoring-stack.yml` | 新建，组件自监控 + Watchdog |
| `alertmanager.yml` | 新增 Watchdog → `null` 子路由 |

备份：`*.bak.2026-10-07-logalert`、`prometheus.yml.bak.2026-10-07-middleware`。

---

## 第一步：Loki ruler

### 1.1 loki-config.yaml 追加

```yaml
ruler:
  # 规则文件:./loki-rules 挂到 /loki/rules/fake(单租户模式租户名为 fake)
  storage:
    type: local
    local:
      directory: /loki/rules
  rule_path: /loki/rules-temp
  alertmanager_url: http://alertmanager:9093
  evaluation_interval: 1m
  enable_api: true
```

### 1.2 compose 挂载规则目录

```yaml
  loki:
    volumes:
      - ./loki-config.yaml:/etc/loki/loki-config.yaml
      - ./loki-rules:/loki/rules/fake:ro
      - loki-data:/loki
```

> ⚠️ **规则必须放在 `<directory>/<租户名>/` 下**。`auth_enabled: false` 时租户名固定是 `fake`，所以是 `/loki/rules/fake/*.yml`。没配置前 Loki 的 `/loki/api/v1/rules` 会报 `unable to read rule dir /loki/rules/fake`，看到这个就说明 ruler 还没有规则目录。

### 1.3 校验 & 生效

```bash
docker run --rm -v $PWD/loki-config.yaml:/etc/loki/c.yaml grafana/loki:3.7.3 \
  -config.file=/etc/loki/c.yaml -verify-config; echo "exit=$?"     # exit=0 即通过
docker compose up -d loki          # 改了挂载，要重建容器

# 规则加载情况(Prometheus 兼容接口)
curl -s localhost:3100/prometheus/api/v1/rules | jq -r '.data.groups[].rules[] | "\(.health)\t\(.state)\t\(.name)"'
```

> 重启 Loki 时日志里会短暂出现 `error getting ingester clients: empty ring`，等 ingester 就绪（约 15s）后会自动消失；Alloy 会重试补发，不丢日志。

---

## 第二步：日志告警规则 loki-rules/log-alerts.yml

### 2.1 先看基线再定阈值

上线前用 `query_range` 统计过去 24h 每 10 分钟的最大值，避免一上线就刷屏：

```bash
qr(){ curl -s -G localhost:3100/loki/api/v1/query_range --data-urlencode "query=$1" \
  --data-urlencode "start=$(date -d '-24 hours' +%s)" --data-urlencode "end=$(date +%s)" --data-urlencode step=600; }

# 每个容器 error 日志 /10m 的 24h 最大值
qr 'sum by (container_name) (count_over_time({job="docker-host"} |~ "(?i)\\b(error|fatal|panic)\\b" [10m]))' \
  | jq -r '.data.result[] | "\(.metric.container_name)\t\([.values[][1]|tonumber]|max)"' | sort -t$'\t' -k2 -nr
```

> LogQL **不支持 PromQL 的子查询**（`max_over_time(...[24h:10m])` 会报错），要统计历史峰值只能用 `query_range` 拉回来自己算。

2026-10-07 基线：容器 error 最多 44 条/10m（blackbox），SSH 失败 0 次，成功登录来源只有 192.168.31.243 / 192.168.31.4。

### 2.2 规则

| 告警 | 条件 | 级别 |
|---|---|---|
| DiskIOError | syslog 出现 `I/O error` / `EXT4-fs error` / `Buffer I/O error` / `blk_update_request` | critical |
| SSHBruteForce | 10 分钟 SSH 认证失败 > 20 次 | warning |
| SSHLoginFromOutside | 非 192.168.* / 127.0.0.1 来源 SSH 登录成功 | critical |
| ContainerErrorSpike | 单个容器 10 分钟 error/fatal/panic 日志 > 100 条 | warning |
| FrpcReconnecting | 10 分钟 frpc 连接 ECS 失败 > 3 次 | warning |
| LogIngestionStopped | docker-host / agent / bastion / middleware 任一台 15 分钟没有任何日志 | critical |

```yaml
groups:
  - name: log-alerts
    interval: 1m
    rules:
      - alert: DiskIOError
        expr: |
          label_replace(
            sum by (host) (count_over_time({job="syslog"} |~ "I/O error|EXT4-fs error|Buffer I/O error|blk_update_request" [10m])),
            "instance", "$1", "host", "(.*)"
          ) > 0
        labels:
          severity: critical
        annotations:
          summary: '内核报磁盘 I/O 错误: {{ $labels.instance }}'
          description: '最近 10 分钟 syslog 出现 {{ $value }} 条磁盘 I/O 错误,可能是坏道,用 dmesg -T | grep -i error 查看是哪块盘。'

      - alert: SSHBruteForce
        expr: |
          label_replace(
            sum by (host) (count_over_time({job="authlog"} |~ "Failed password|Invalid user|authentication failure" [10m])),
            "instance", "$1", "host", "(.*)"
          ) > 20
        labels:
          severity: warning
        annotations:
          summary: 'SSH 登录失败过多: {{ $labels.instance }}'
          description: '最近 10 分钟 SSH 认证失败 {{ $value }} 次,可能在被爆破。'

      - alert: SSHLoginFromOutside
        expr: |
          label_replace(
            sum by (host) (count_over_time({job="authlog"} |~ "Accepted \\S+ for \\S+ from" !~ "from (192\\.168\\.|127\\.0\\.0\\.1)" [5m])),
            "instance", "$1", "host", "(.*)"
          ) > 0
        labels:
          severity: critical
        annotations:
          summary: 'SSH 从非内网地址登录成功: {{ $labels.instance }}'
          description: '最近 5 分钟有 {{ $value }} 次来自非内网地址的 SSH 登录,确认是不是自己。'

      - alert: ContainerErrorSpike
        expr: |
          label_replace(
            sum by (container_name) (count_over_time({job="docker-host"} |~ "(?i)\\b(error|fatal|panic)\\b" [10m])),
            "instance", "$1", "container_name", "(.*)"
          ) > 100
        labels:
          severity: warning
        annotations:
          summary: '容器错误日志激增: {{ $labels.instance }}'
          description: '最近 10 分钟 {{ $labels.instance }} 输出 {{ $value }} 条 error/fatal/panic 日志。'

      # 2026-10-07 初版规则；后续标签偏差已按用户确认修复
      - alert: FrpcReconnecting
        expr: |
          label_replace(
            sum by (host) (count_over_time({job="frpc"} |= "connect to server error" [10m])),
            "instance", "$1", "host", "(.*)"
          ) > 3
        labels:
          severity: warning
        annotations:
          summary: 'frp 隧道反复断线: {{ $labels.instance }}'
          description: '最近 10 分钟 frpc 连接 ECS frps 失败 {{ $value }} 次,公网服务(ntfy 等)可能不可用。检查 ECS 上 frps 和家里网络。'

      - alert: LogIngestionStopped
        expr: |
          label_replace(absent_over_time({host="docker-host"}[15m]), "instance", "docker-host", "", "")
          or
          label_replace(absent_over_time({host="agent"}[15m]), "instance", "agent", "", "")
          or
          label_replace(absent_over_time({host="bastion"}[15m]), "instance", "bastion", "", "")
          or
          label_replace(absent_over_time({host="middleware"}[15m]), "instance", "middleware", "", "")
        labels:
          severity: critical
        annotations:
          summary: '日志断流: {{ $labels.instance }}'
          description: 'Loki 超过 15 分钟没收到 {{ $labels.instance }} 的任何日志,检查那台机器上的 Alloy。'
```

> 历史核验：2026-10-15 曾观察到 bastion Loki stream 为 `job="loki.source.journal.frpc"`，与初版规则 selector `{job="frpc"}` 不一致。用户已确认该标签/告警问题已修复并验证；此处保留初次部署时的规则示例。详见 [[Ansible 批量部署 Alloy 实战记录]]。

> ⚠️ **ntfy 模板标题和正文都显示 `instance` 标签**，而日志里没有这个标签（只有 `host` / `container_name`）。用 LogQL 的 `label_replace` 映射成 `instance`，否则推送标题里没有机器名。
> LogQL 字符串里的反斜杠要双写：`\\S`、`\\.`。
> `absent_over_time` 只能针对固定的选择器；以后新增往 Loki 推日志的机器，记得在 LogIngestionStopped 里加一行。

### 2.3 端到端测试（不污染真实告警）

临时加一条只匹配测试标记的规则，写一行 syslog，看它能不能到手机，测完删掉：

```bash
cat > loki-rules/zz-test.yml <<'EOF'
groups:
  - name: pipeline-test
    interval: 1m
    rules:
      - alert: LogAlertPipelineTest
        expr: label_replace(sum by (host) (count_over_time({job="syslog"} |= "LOKI_RULER_PIPELINE_TEST" [5m])), "instance", "$1", "host", "(.*)") > 0
        labels:
          severity: info
        annotations:
          summary: '日志告警链路测试(可忽略)'
EOF
logger "LOKI_RULER_PIPELINE_TEST"
# 约 1~2 分钟后：
curl -s localhost:9093/api/v2/alerts | jq -r '.[] | "\(.status.state)\t\(.labels.alertname)"'
rm loki-rules/zz-test.yml     # ruler 会自动重新加载，不用重启
```

> 不要用伪造的 `I/O error` 日志来测：那会在 syslog 里留下一条误导性的"磁盘错误"记录。用专门的测试标记更干净。
> 规则文件删掉后，Alertmanager 里那条告警要等 endsAt 过期才会恢复，手机会再收到一条"已恢复"。

---

## 第三步：监控组件自监控

### 3.1 prometheus.yml 追加

```yaml
  # ---------- 监控组件自监控 ----------
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'loki'
    static_configs:
      - targets: ['loki:3100']

  - job_name: 'alloy'
    static_configs:
      - targets: ['alloy:12345']
        labels:
          instance: 'docker-host'

  - job_name: 'grafana'
    static_configs:
      - targets: ['grafana:3000']
```

### 3.2 rules/monitoring-stack.yml

| 告警 | 条件 | 级别 |
|---|---|---|
| Watchdog | `vector(1)`，永远触发 | none |
| LogPipelineDown | `up{job=~"loki\|alloy"} == 0` 持续 3m | critical |
| GrafanaDown | `up{job="grafana"} == 0` 持续 5m | warning |
| AlloyDroppingLogs | `increase(loki_write_dropped_entries_total[10m]) > 0` | warning |
| LokiRuleEvaluationFailing | `increase(loki_prometheus_rule_evaluation_failures_total[10m]) > 0` 持续 5m | warning |
| PrometheusRuleEvaluationFailing | `increase(prometheus_rule_evaluation_failures_total[10m]) > 0` 持续 5m | warning |
| PrometheusAlertmanagerUnreachable | `increase(prometheus_notifications_errors_total[10m]) > 0` 持续 5m | critical |

> 指标名先从各组件的 `/metrics` 里 grep 确认再写规则，别凭印象写：Loki ruler 的指标是 `loki_prometheus_rule_*`，Alloy 写 Loki 的指标是 `loki_write_*`。

### 3.3 Watchdog 路由（alertmanager.yml，初版配置）

```yaml
route:
  receiver: 'ntfy'
  routes:
    # 初版部署时送到 null；外部 dead-man 接入后以当前 alertmanager.yml 为准。
    - matchers: ['alertname="Watchdog"']
      receiver: 'null'
```

> Watchdog 本身**不能**发现 Prometheus 挂掉，它需要外部 dead-man 检测其心跳。用户已确认外部检测接入完成；上面的 `null` 路由是初版示例，不代表当前 Alertmanager 配置。

### 3.4 校验 & 生效（热加载，不重启）

```bash
docker run --rm -v $PWD:/cfg --entrypoint promtool prom/prometheus:latest check config /cfg/prometheus.yml
docker run --rm -v $PWD:/cfg --entrypoint amtool prom/alertmanager:latest check-config /cfg/alertmanager.yml
docker kill -s HUP prometheus alertmanager       # SIGHUP 重新加载配置

curl -s localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job)\t\(.health)"'
curl -s localhost:9093/api/v2/alerts | jq -r '.[] | "\(.labels.alertname)\treceivers=\([.receivers[].name]|join(","))"'
# 初版 null 路由的预期；当前应按已部署的外部 dead-man receiver 验证
```

> Prometheus 没开 `--web.enable-lifecycle`，不能 `curl -XPOST /-/reload`，但 **SIGHUP 一样能热加载**，不用重启容器。
> 在 Prometheus 容器里用 `wget http://loki:3100` 会报 `bad address`，是 busybox wget 的解析问题，不代表网络不通；Prometheus 自己抓取正常（看 targets 页面）。

---

## 第四步：注释掉 middleware

middleware（192.168.31.6）能 ping 通但 9100 拒绝连接，NodeDown 从 10-06 22:32 一直在响。先从抓取目标注释掉：

```yaml
      # middleware 的 node_exporter 已停(2026-10-07 注释)
      # - targets:
      #     - '192.168.31.6:9100'
      #   labels:
      #     instance: 'middleware'
```

`docker kill -s HUP prometheus` 后，target 消失，规则下一轮评估时 NodeDown 恢复，ntfy 推送"已恢复"。

> 更正：后来通过 Ansible 上机查看，middleware 上**根本没装过 node_exporter**（Prometheus 一直在抓一个不存在的端口），不是"停了"。已改装 Alloy，以 remote write 推送指标，这行抓取配置不再需要。见 [[Ansible 批量部署 Alloy 实战记录]]。

---

## 上线当天就发现的问题

配置 DiskIOError 前查基线时，在 docker-host 的 syslog 里发现：

```
kernel: I/O error, dev sdb, sector 1471431 op 0x0:(READ) ...
sd 1:0:0:2: [sdb] ... Sense Key : Aborted Command
```

- `sdb` 是 PVE 透传给 docker-host 的 QEMU 虚拟盘，挂在 `/mnt/jellyfin`；
- 10-05 15:30 和 10-07 15:32 两次，都是**同一个扇区**读失败，大概率是 PVE 宿主机物理盘有坏道；
- 虚拟机里看不到 SMART，需要在 PVE 宿主机上执行 `smartctl -a /dev/<物理盘>`，重点看 Reallocated / Pending / Uncorrectable。

这正是日志告警的价值：错误已经出现两次，之前没人知道。之后再出现会直接推到手机。

---

## 排障清单

| 症状 | 原因 | 处理 |
|---|---|---|
| `/loki/api/v1/rules` 报 `unable to read rule dir /loki/rules/fake` | ruler 没有规则目录 | 规则挂到 `/loki/rules/fake/` |
| 规则加载了但告警到不了 AM | 没配 `ruler.alertmanager_url` | 加上并重建 Loki |
| 推送标题没有机器名 | 日志告警没有 `instance` 标签 | `label_replace` 映射 |
| LogQL 子查询报 `parse error` | LogQL 不支持 `[24h:10m]` | 用 `query_range` 统计 |
| 删了规则后告警一直 active | AM 等 endsAt 过期 | 等几分钟自动恢复 |
| AlloyDroppingLogs 突然出现，丢的都是旧时间戳 | 有容器在崩溃循环，Alloy 每次重启都从头重读它的日志 | 见 [[容器监控与告警（cAdvisor + Docker 重启次数）]] |
| Prometheus 容器 `wget` 报 `bad address` | busybox wget 问题 | 以 targets 页面为准 |

---

## 日常运维

| 操作 | 命令 |
|---|---|
| 改日志告警规则 | 编辑 `loki-rules/*.yml`，ruler 自动重新加载；`curl -s localhost:3100/prometheus/api/v1/rules` 确认 |
| 改 Loki 配置 | `-verify-config` 校验 → `docker compose up -d loki` |
| 改 Prometheus 规则 / 抓取 | promtool 校验 → `docker kill -s HUP prometheus` |
| 查日志告警当前状态 | `curl -s localhost:3100/prometheus/api/v1/alerts` |
| 试一条 LogQL | `curl -s -G localhost:3100/loki/api/v1/query --data-urlencode 'query=...'` |

---

