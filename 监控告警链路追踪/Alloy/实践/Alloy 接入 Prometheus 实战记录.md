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
| Prometheus `/api/v1/label/job/values` 含 `alloy` | 端到端通 |
| `alloy_build_info` series 存在 | self-scrape 也推过去了 |

WAL 增长 ≠ batch 已发——只看 WAL 容易误判"还没发"，要结合 `bytes_total` 一起看。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] — 笔记配方来源
- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — Pipeline 模式
- [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] — reload vs restart 行为差异
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 之前判断为"知识存档，不急着部署"，本次小范围打通 homelab

