---
publish: true
tags:
  - cAdvisor
  - Docker
  - Prometheus
  - 告警
  - homelab
---
> 日期：2026-10-07
> 背景：docker-host 上的 `pve-mysql` 因为没拿到 root 密码，从 10-02 起崩溃重启了 **6934 次**，5 天里没有任何告警直接报出来。最后是因为 Alloy 每次都把它的日志从头重读、旧日志被 Loki 拒收，触发了 AlloyDroppingLogs，才被间接发现。本次补上容器级监控。
> 前置：[[Prometheus 告警 → ntfy 手机推送]]、[[Loki 日志告警与监控组件自监控]]

---

## 结论先说

| 想发现的问题 | 数据来源 | 原因 |
|---|---|---|
| 容器反复重启 | **Docker 自己的 `RestartCount`**（textfile 导出） | cAdvisor 识别不了同一容器的重启 |
| 容器 OOM | cAdvisor `container_oom_events_total` | |
| 内存接近上限 | cAdvisor working set / limit | 只对设了上限的容器有效 |
| 容器消失（停止/删除/崩溃） | cAdvisor `container_last_seen` | |

> ⚠️ **cAdvisor 的 `container_start_time_seconds` 不能用来判断重启**：测试容器 `--restart=always` 每 20 秒退出一次，Docker 记录重启 7 次，cAdvisor 报的启动时间始终是第一次的值，`changes()` 结果为 0。重启检测必须用 Docker 的 `RestartCount`。

---

## 第一步：部署 cAdvisor

### 1.1 compose（`/root/monitoring/docker-compose.yml`）

```yaml
  # 容器级指标:重启、OOM、资源。只在 docker 内网给 Prometheus 抓,不映射端口
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.54.1
    container_name: cadvisor
    restart: unless-stopped
    privileged: true
    devices:
      - /dev/kmsg
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    command:
      - '--docker_only=true'
      - '--housekeeping_interval=30s'
      - '--store_container_labels=false'
      - '--disable_metrics=advtcp,cpu_topology,cpuset,hugetlb,percpu,perf_event,process,referenced_memory,resctrl,sched,tcp,udp'
```

> ⚠️ **Docker 29 要用 cAdvisor v0.54.1 及以上**。Docker 29 默认使用 containerd snapshotter（`docker info` 显示 `driver-type io.containerd.snapshotter.v1`），v0.52.1 会刷屏报 `failed to identify the read-write layer ID ... layerdb/mounts/...: no such file or directory`，指标里**没有任何容器名**。换 v0.54.1 后正常识别。
> `--store_container_labels=false` + `--disable_metrics=...` 控制序列数量：29 个容器约 1900 条序列。
> 不映射端口，cAdvisor 的 Web UI 没有鉴权。

```bash
docker compose up -d cadvisor
docker logs cadvisor 2>&1 | grep -c 'Failed to process watch event'     # 应为 0
```

### 1.2 Prometheus 抓取

```yaml
  # 容器指标(cAdvisor),只保留有名字的容器
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
        labels:
          instance: 'docker-host'
    metric_relabel_configs:
      - source_labels: [name]
        regex: ''
        action: drop
```

> cAdvisor 还会报各个 cgroup（system.slice 等）的指标，它们没有 `name` 标签，用 `metric_relabel_configs` 丢掉。

---

## 第二步：用 Docker RestartCount 检测重启

node_exporter 的 textfile collector + 一个 systemd timer，每 30 秒把 `docker inspect` 的结果写成指标。

### 2.1 脚本 `/usr/local/bin/docker-state-textfile.sh`

```bash
#!/bin/bash
# 把 docker 容器状态写成 node_exporter textfile 指标。
# 由 docker-state-textfile.timer 每 30s 调用;cAdvisor 识别不了同一容器的反复重启,所以用 Docker 自己的 RestartCount。
set -euo pipefail
DIR=/var/lib/node_exporter/textfile
OUT="$DIR/docker_state.prom"
TMP=$(mktemp "$DIR/.docker_state.XXXXXX")
trap 'rm -f "$TMP"' EXIT

ids=$(docker ps -aq)
json='[]'
[ -n "$ids" ] && json=$(docker inspect $ids)

metric() {  # 名称 类型 说明 jq表达式(值)
  echo "# HELP $1 $3"
  echo "# TYPE $1 $2"
  jq -r --arg m "$1" ".[] | \"\(\$m){name=\\\"\(.Name|ltrimstr(\"/\"))\\\",restart_policy=\\\"\(.HostConfig.RestartPolicy.Name)\\\"} \($4)\"" <<<"$json"
}
{
  metric docker_container_restart_count gauge "Docker RestartCount(容器重建后归零)" '.RestartCount'
  metric docker_container_running gauge "容器是否在运行" '(if .State.Running then 1 else 0 end)'
  metric docker_container_oom_killed gauge "上次退出是否因 OOM" '(if .State.OOMKilled then 1 else 0 end)'
  metric docker_container_exit_code gauge "上次退出码" '.State.ExitCode'
} > "$TMP"
chmod 644 "$TMP"
mv "$TMP" "$OUT"
```

> 先写临时文件再 `mv`：node_exporter 永远读到完整的文件，不会读到写了一半的。
> 同一个指标的所有样本必须连续输出（HELP/TYPE 后跟全部容器），所以按指标分四次调用 jq，而不是按容器循环。

### 2.2 systemd timer

`/etc/systemd/system/docker-state-textfile.service`：

```ini
[Unit]
Description=Export docker container state for node_exporter textfile collector
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/docker-state-textfile.sh
```

`/etc/systemd/system/docker-state-textfile.timer`：

```ini
[Unit]
Description=Run docker-state-textfile every 30s

[Timer]
OnBootSec=30s
OnUnitActiveSec=30s
AccuracySec=1s

[Install]
WantedBy=timers.target
```

### 2.3 node_exporter 开启 textfile

`/etc/systemd/system/node_exporter.service`：

```ini
ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory=/var/lib/node_exporter/textfile
```

```bash
mkdir -p /var/lib/node_exporter/textfile
chmod 755 /usr/local/bin/docker-state-textfile.sh
systemctl daemon-reload
systemctl enable --now docker-state-textfile.timer
systemctl restart node_exporter

curl -s localhost:9100/metrics | grep -E '^docker_container_restart_count|^node_textfile_scrape_error'
# node_textfile_scrape_error 0 表示文件格式正确
```

指标由已有的 `job="node"`（docker-host）抓取，不用改 Prometheus 配置。

---

## 第三步：告警规则 rules/containers.yml

| 告警 | 条件 | 级别 |
|---|---|---|
| ContainerRestartLoop | 15 分钟内 RestartCount 增加 ≥ 3 | critical |
| ContainerOOMKilled | 10 分钟内发生 OOM | warning |
| ContainerMemoryNearLimit | working set > 上限的 90%，持续 10m | warning |
| ContainerDisappeared | 10 分钟前还在、现在没了 | warning |
| CAdvisorDown（在 monitoring-stack.yml） | 抓不到 cAdvisor 5m | warning |

```yaml
groups:
  - name: containers
    interval: 30s
    rules:
      - alert: ContainerRestartLoop
        expr: |
          label_replace(
            increase(docker_container_restart_count{job="node"}[15m]),
            "instance", "$1", "name", "(.*)"
          ) >= 3
        labels:
          severity: critical
        annotations:
          summary: '容器反复重启: {{ $labels.instance }}'
          description: '{{ $labels.instance }} 最近 15 分钟重启了约 {{ $value | printf "%.0f" }} 次,用 docker logs --tail 50 {{ $labels.instance }} 看退出原因。'

      - alert: ContainerOOMKilled
        expr: |
          label_replace(
            increase(container_oom_events_total{job="cadvisor"}[10m]),
            "instance", "$1", "name", "(.*)"
          ) > 0
        labels:
          severity: warning
        annotations:
          summary: '容器内存溢出(OOM): {{ $labels.instance }}'

      - alert: ContainerMemoryNearLimit
        expr: |
          label_replace(
            container_memory_working_set_bytes{job="cadvisor"}
              / (container_spec_memory_limit_bytes{job="cadvisor"} > 0),
            "instance", "$1", "name", "(.*)"
          ) > 0.9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: '容器内存接近上限: {{ $labels.instance }}'

      - alert: ContainerDisappeared
        expr: |
          label_replace(
            count by (name) (container_last_seen{job="cadvisor"} offset 10m)
              unless count by (name) (container_last_seen{job="cadvisor"}),
            "instance", "$1", "name", "(.*)"
          )
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: '容器消失: {{ $labels.instance }}'
          description: '10 分钟前还在运行,现在没了。约 10 分钟后此告警自动恢复,不代表容器已恢复。'
```

> `instance` 统一改成容器名，ntfy 标题直接显示是哪个容器。
> `increase` 能正确处理计数归零（容器被重建时 RestartCount 从 0 开始）。
> ContainerDisappeared 是"变化检测"：实测容器删除后约 **6~7 分钟**触发（`offset 10m` 加上 5 分钟回看窗口，再加 `for: 1m`），之后一段时间自动恢复。主动 `docker stop` 也会触发一次，可以忽略。
> 目前 docker-host 上没有容器设置内存上限，ContainerMemoryNearLimit 暂时不会触发。

---

## 第四步：测试（不打扰手机）

先在 Alertmanager 里静默测试容器，再造一个反复重启的容器：

```bash
docker exec alertmanager amtool silence add --alertmanager.url=http://localhost:9093 \
  instance=cadvisor-test --duration=40m --comment="容器告警测试"
docker run -d --name cadvisor-test --restart=always alpine:3 sh -c 'sleep 20; exit 1'

# 2~3 分钟后
curl -s localhost:9090/api/v1/alerts | jq -r '.data.alerts[] | select(.labels.instance=="cadvisor-test") | "\(.state) \(.labels.alertname)"'
curl -s localhost:9093/api/v2/alerts | jq -r '.[] | select(.labels.instance=="cadvisor-test") | "\(.labels.alertname) \(.status.state)"'
# ContainerRestartLoop firing，AM 里 suppressed（被静默）

docker rm -f cadvisor-test     # 约 6~7 分钟后 ContainerDisappeared 触发，同样被静默
```

---

## pve-mysql 事件处理

- 原因：容器创建时 `MYSQL_ROOT_PASSWORD` 为空，数据目录又未初始化，MySQL 启动即退出（`Database is uninitialized and password option is not specified`），`restart: always` 让它每分钟重启一次。
- 处理：项目暂不用，停掉并关闭自动重启：

```bash
docker update --restart=no pve-mysql
docker stop pve-mysql
```

> ⚠️ pveui 的 compose 里仍是 `restart: always`，在 `/root/workspace/pveui` 执行 `docker compose up -d` 会按原配置重建、重新开始崩溃循环。恢复前先在 `.env` 填好 `MYSQL_ROOT_PASSWORD`。

### 为什么崩溃循环会触发 AlloyDroppingLogs

`loki.source.docker` 在容器每次重新启动时，会把这个容器的日志从头再读一遍。崩溃循环的容器日志里有几天前的条目，Loki 拒收（`entry too far behind`），Alloy 重试后丢弃。所以 **AlloyDroppingLogs 突然出现、且丢弃的都是旧时间戳时，先查有没有容器在反复重启**：

```bash
docker logs --since 30m alloy 2>&1 | grep -oE 'container=docker/[0-9a-f]{12}' | sort | uniq -c | sort -rn
docker ps -a --no-trunc --format '{{.ID}} {{.Names}} {{.Status}}' | grep <上面的ID>
```

---

## 日常运维

| 操作 | 命令 |
|---|---|
| 看哪些容器重启过 | `curl -s localhost:9100/metrics \| grep '^docker_container_restart_count' \| grep -v ' 0$'` |
| textfile 是否正常 | `systemctl list-timers docker-state-textfile.timer`；`node_textfile_scrape_error` 为 0 |
| 容器资源排行 | PromQL：`topk(10, sum by (name) (rate(container_cpu_usage_seconds_total{job="cadvisor"}[5m])))` |
| 内存排行 | `topk(10, container_memory_working_set_bytes{job="cadvisor"})` |

## 改动文件与备份

| 位置 | 文件 |
|---|---|
| `/root/monitoring/` | `docker-compose.yml`（+cadvisor）、`prometheus.yml`（+cadvisor job）、`rules/containers.yml`（新）、`rules/monitoring-stack.yml`（+CAdvisorDown） |
| docker-host 系统 | `/usr/local/bin/docker-state-textfile.sh`、`docker-state-textfile.{service,timer}`、`node_exporter.service`（+textfile 参数） |
| 备份 | `/root/monitoring/*.bak.2026-10-07-cadvisor`（含 `node_exporter.service`、`monitoring-stack.yml`） |
