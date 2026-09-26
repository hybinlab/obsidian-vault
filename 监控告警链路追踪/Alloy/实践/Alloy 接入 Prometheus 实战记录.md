---
publish: true
tags:
  - Alloy
  - Prometheus
  - homelab
cssclasses:
  - Alloy
---

把本机 systemd alloy 的指标推到 docker-host（`.1`）上 Prometheus 的实战记录，对应 [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] 配方落地。过程踩了三个坑，全记下来下次别再踩。

## 最终结果

链路通：alloy → `http://192.168.31.1:9090/api/v1/write` → docker-host Prometheus :9090。

验证三个独立证据：
1. `curl 127.0.0.1:12345/metrics` 看 `prometheus_remote_storage_bytes_total{url="http://192.168.31.1:9090/api/v1/write"} > 0`
2. `curl 192.168.31.1:9090/api/v1/label/job/values` 含 `alloy` 和 `integrations/unix`
3. `curl 192.168.31.1:9090/api/v1/series?match[]=alloy_build_info` 能查到 series，标签里 `job="alloy"`、`instance="127.0.0.1:12345"`

## 最终配置

`/etc/alloy/config.alloy`（备份在 `.bak.2026-09-25`）：

```alloy
logging {
  level = "warn"
}

prometheus.exporter.unix "default" {
  include_exporter_metrics = true
  disable_collectors       = ["mdadm"]
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://192.168.31.1:9090/api/v1/write"
  }
}

prometheus.scrape "default" {
  targets = array.concat(
    prometheus.exporter.unix.default.targets,
    [{
      job         = "alloy",
      __address__ = "127.0.0.1:12345",
    }],
  )

  forward_to = [prometheus.remote_write.default.receiver]
}
```

`/root/monitoring/docker-compose.yml`（docker-host）prometheus service 加一行：

```yaml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-remote-write-receiver'   # ← 新增
    restart: always
```


## 坑一：`/-/reload` 返回 200 ≠ 真的生效

改完 `/etc/alloy/config.alloy` 的 URL 后调 `curl -X POST http://127.0.0.1:12345/-/reload`，返回 `config reloaded` + `Alloy is ready`，**但 alloy 进程仍在用旧 URL 发 batch**。`journalctl -u alloy` 看出真相：

```
Sep 25 22:03:59 alloy[1326]: Failed to send batch, retrying
  url=http://192.168.31.4:9090/api/v1/write
  err="dial tcp 192.168.31.4:9090: connect: connection refused"
```

每分钟一次，从 21:56 一直重试到 22:11——reload handler 被 batch retry 阻塞，没真的重读 config。

**判别法**：`/metrics` 里看 `prometheus_remote_storage_*{url="..."}`，跟配置文件里的 URL 对比，不一致就是没生效。

**正解**：直接 `systemctl restart alloy`，PID 换新，journal 看 `Started alloy.service` 时间戳。重启后 URL 标签立刻切到 `.1`，batch 正常 flush。

## 坑三：Prometheus 必须显式开 receiver

docker-host Prometheus 容器启动命令只有：

```
--config.file=/etc/prometheus/prometheus.yml
--storage.tsdb.path=/prometheus
--storage.tsdb.retention.time=30d
```

**没有** `--web.enable-remote-write-receiver`——Prometheus 默认二进制**默认不开**这个 receiver（2.x+ 都要显式 flag 开启）。后果：`POST /api/v1/write` 返回 **404**，不是 405。

- 404 = 端点没注册（receiver 没开）
- 405 = 端点存在但方法不对（receiver 开了）

判别用空 body POST 一个请求（`printf '' | curl -X POST ... /api/v1/write`），404 就是没开。改 compose 加 flag，`docker compose up -d prometheus` 重启容器即可。重启会让内存里 in-memory head（约 2h 内未落盘样本）丢失，已落盘的 TSDB（挂卷）保留。

## 坑四：`out of order sample` —— 排除三个假设之后才找到真根因

现象：`journalctl -u alloy` 每分钟报一次，`failedSampleCount` 稳定在 485~486，持续报了快 20 分钟不停：

```
level=error msg="non-recoverable error" component_id=prometheus.remote_write.default
url=http://192.168.31.1:9090/api/v1/write
err="server returned HTTP status 400 Bad Request: out of order sample\n"
```

`out of order sample` 是 Prometheus TSDB 的特征报错：**同一个 series（相同 label 组合）被写入了一个比已存储时间戳更早/相等的样本**。排查过程依次排除了三个假设，第四个才是真根因——记录下每一步的判别法，比记结论更有用：

**假设一：Prometheus 同时用 pull 又用 push 采集同一台机器**（一开始最先怀疑的）。检查 `prometheus.yml` 发现 `job_name: 'node'` 下确实还留着一条 agent 机器的 `static_configs`（`192.168.31.4:9100`，`instance: 'agent'`）——这是 agent 迁移到 Alloy push 模式之前的历史配置，删掉这条、`docker compose restart prometheus` 后，报错**没有消失**。✗ 排除。

> 后续把这条 `static_configs` 加回去验证过，确实不影响——因为 agent 的 9100 端口根本没有 node_exporter 在监听，Prometheus 去 scrape 只会失败，失败的 scrape 只写一条 `up{job="node",instance="agent"}=0` 元数据，跟 Alloy push 的真实指标名（`node_cpu_seconds_total` 等）完全不重叠，所以不会真正冲突。**这个"留着没事"的结论是有前提的**——前提是 pull 那侧压根没有真实数据源，如果哪天真在这个端口装了 node_exporter，冲突会重新出现，到时候这条 `static_configs` 还是要删。

**假设二：agent 机器上跑了两个 alloy 进程**（比如调试时手动前台跑过一次忘了杀）。`ps aux | grep alloy` 只有一个 systemd 管的进程。✗ 排除。

**假设三：agent 机器系统时钟跳变**（VM 挂起恢复常见问题，clock 往回跳会导致自己跟自己的历史数据打架）。`timedatectl status` 显示 `System clock synchronized: yes`，`NTP service: active`。✗ 排除。

**假设四（真根因）：`instance` 标签默认值没有唯一性**。`discovery.relabel "unix_job"` 只 relabel 了 `job`，从没设置过 `instance`。Prometheus 规则：target 没有显式 `instance` 时自动拿 `__address__` 填充；而 `prometheus.exporter.unix` 是**内嵌**在 Alloy 进程里的虚拟采集，它的 `__address__` 就是 Alloy 自己的监听地址 `127.0.0.1:12345`——**这个值对任何一台跑 Alloy 的机器都长得一样，天生没有唯一性**。验证：

```bash
curl -s http://192.168.31.1:9090/api/v1/label/instance/values
# {"data":["127.0.0.1:12345","agent","bastion","database","docker-host","middleware","mysql"]}
```

`127.0.0.1:12345` 真的作为一个 instance 值存在，混在其他手动命名的机器名里——确认了这条 series 缺乏唯一标识，是导致持续冲突的设计缺陷。

**判别法**：`out of order sample` 报错如果是**持续性、每个周期都全批失败**（不是偶发一两次），优先级排查顺序是：① Prometheus 端有没有 pull+push 重叠 → ② 采集端有没有重复进程 → ③ 采集端时钟是否同步 → ④ 有没有用了非唯一的默认标签值（尤其是内嵌/虚拟 exporter，`__address__` 默认值很可能是 loopback 地址）。

**正解**：显式给 `instance` 标签 relabel，用这台机器的真实 hostname：

```alloy
discovery.relabel "unix_job" {
  targets = prometheus.exporter.unix.default.targets

  rule {
    target_label = "job"
    replacement  = "node"
  }

  rule {
    target_label = "instance"
    replacement  = constants.hostname   // 原生 systemd 装的 alloy 用这个没问题
  }
}
```

`constants.hostname` 在这里能用是因为 alloy 是**原生 systemd 装的**，没有容器 hostname 命名空间隔离；如果是 Docker 部署的 alloy，`constants.hostname` 拿到的会是容器 ID，得改用环境变量传真实 hostname（见 [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] 里那个坑）。

**教训**：内嵌/虚拟类型的 exporter 组件（`prometheus.exporter.unix` 这种没有真实网络地址的）容易在 `instance` 标签上留坑，写完 `discovery.relabel` 别只顾着改 `job`，`instance` 也要显式检查一遍是不是默认成了 loopback 地址。

## 探测工具陷阱

`(timeout 2 bash -c "echo > /dev/tcp/H/P")` 在子 shell 里报"Connection refused"和"closed/filtered" 都可能是探测器自身问题，**不是网络真被拒**。这次差点因这个误判把整个链路放弃。

**正解**：
- `timeout 3 bash -c 'exec 3<>/dev/tcp/H/P && echo OPEN'` 拿真 TCP 状态
- `curl -sS -o /dev/null -w "%{http_code}" http://H:P/-/ready` 拿真 HTTP 状态码

## 诊断信号对照

| 看什么 | 含义 |
| --- | --- |
| `prometheus_remote_write_wal_samples_appended_total` 增长 | scrape 在产样本、写进了 WAL |
| `prometheus_remote_storage_bytes_total` 增长 | batch 真发出去、被对端收下 |
| `prometheus_remote_storage_samples_rejected_total` 增长 | 发了但被对端拒（protobuf 错误等） |
| `journalctl -u alloy` `Failed to send batch, retrying` | 网络层失败，对端连不上 |
| `err="...HTTP status 400 Bad Request: out of order sample"` | 持续/全批失败先排查 pull+push 重叠 → 重复进程 → 时钟同步 → `instance` 是不是用了非唯一的默认值（loopback 地址） |
| `curl .../api/v1/label/instance/values` 里出现 `127.0.0.1:xxxxx` 这类地址 | 内嵌 exporter 组件没显式设置 `instance`，落到了 `__address__` 默认值 |
| Prometheus `/api/v1/label/job/values` 含 `alloy` | 端到端通 |
| `alloy_build_info` series 存在 | self-scrape 也推过去了 |

WAL 增长 ≠ batch 已发——只看 WAL 容易误判"还没发"，要结合 `bytes_total` 一起看。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] — 笔记配方来源
- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — Pipeline 模式
- [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] — reload vs restart 行为差异
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 之前判断为"知识存档，不急着部署"，本次小范围打通 homelab
- [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]] — database 机器同款套路 + mysqld_exporter 迁移

