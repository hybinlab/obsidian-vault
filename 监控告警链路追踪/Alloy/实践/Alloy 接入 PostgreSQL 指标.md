---
publish: true
tags:
  - Alloy
  - Prometheus
  - PostgreSQL
  - homelab
cssclasses:
  - Alloy
---

database 机器在 node + mysql 的基础上把 `postgres_exporter` 也并进同一个 Alloy 进程，复用 [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]] 里那套凭据注入和 `instance` 标签唯一性踩坑经验。

## 前置：PostgreSQL 这边的监控账号

走实用主义先用 `postgres` 超级用户把链路跑通，长期再切最小权限专用角色。理由：

- 跟 [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]] 一样，最小权限账号要给一堆 `pg_*` 权限，搭一遍要试错；先跑通再收紧
- PG exporter 监听 9187 是本机端口，安全边界已经够小

## 凭据注入

跟 MySQL 同套路：密码走 systemd EnvironmentFile 注入，alloy 配置里 `sys.env()` 取值。

```bash
# /etc/default/alloy 追加
POSTGRES_EXPORTER_PASSWORD=postgres超级用户密码
```

## 完整配置（database 机器，node + mysql + postgres 合并）

```alloy
// ---- postgres 指标 ----
prometheus.exporter.postgres "default" {
  data_source_names = ["postgresql://postgres:" + sys.env("POSTGRES_EXPORTER_PASSWORD") + "@localhost:5432/postgres?sslmode=disable"]
}

discovery.relabel "postgres_job" {
  targets = prometheus.exporter.postgres.default.targets

  rule {
    target_label = "job"
    replacement  = "postgres"
  }

  rule {
    target_label = "instance"
    replacement  = constants.hostname
  }
}
```

`prometheus.scrape.default.targets` 里 `array.concat` 末尾追加一行，把 postgres 块也并进来：

```alloy
prometheus.scrape "default" {
  targets = array.concat(
    discovery.relabel.node_job.output,
    discovery.relabel.mysql_job.output,
    discovery.relabel.postgres_job.output,
    [{
      job         = "alloy",
      __address__ = "127.0.0.1:12345",
    }],
  )

  forward_to = [prometheus.remote_write.default.receiver]
}
```

## 踩坑记录

### `data_source_name` 不是合法属性

第一版照搬 mysql 的写法写 `data_source_name = "..."`，reload 报：

```
decoding configuration: /etc/alloy/config.alloy:49:3: unrecognized attribute name "data_source_name"
```

postgres exporter 真实属性是 **`data_source_names`（复数 + 数组）**——支持多 DSN 实例。改完 reload 即通。

参考 [[监控告警链路追踪/Alloy/Alloy 数据类型.md]] 里的 Secret 类型说明。

### 默认 exporter 进程起不来

reload 通过不等于连得通。如果 `POSTGRES_EXPORTER_PASSWORD` 写错，exporter 会一直刷 `pq: password authentication failed` 但进程**仍在跑**（只是 scrape 拿不到样本）。验证方式：

```bash
ss -ltnp | grep 9187   # exporter 应该监听到 9187
journalctl -u alloy --since "1 minute ago"
```

## 备份

本次改动前的版本留在 `/etc/alloy/config.alloy.bak.2026-09-28`，env 文件备份在 `/etc/default/alloy.bak.2026-09-28`。

## 验证

```bash
# 1. exporter 监听 9187
ss -ltnp | grep 9187

# 2. alloy 进程收到密码
cat /proc/$(pgrep -f "alloy run")/environ | tr '\0' '\n' | grep POSTGRES

# 3. Prom 端有 postgres job 数据
curl -s 'http://192.168.31.1:9090/api/v1/query?query=pg_up{job="postgres"}' | jq .
```

## 遗留

- 长期要把 `postgres` 超级用户换成专用 `pg_exporter` 角色（最小权限）
- [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]] 同款问题：`/etc/default/alloy` 文件权限 644，明文密码——跟 USER PROFILE 红线冲突，**先跑通**妥协
- MySQL exporter 仍在报 1045（`MYSQL_EXPORTER_PASSWORD` env 有值但跟 MySQL 实际密码对不上），跟本次 PG 链路**独立**，另立任务