---
publish: true
tags:
  - Alloy
  - Prometheus
  - homelab
cssclasses:
  - Alloy
---

database 机器从"独立装 mysqld_exporter"（旧方案见 [[mysql部署prometheus]]）迁移到 Alloy 内置 `prometheus.exporter.mysql`，跟这台机器的 node 指标合并成一个 Alloy 进程，复用 [[监控告警链路追踪/Alloy/实践/Alloy 接入 Prometheus 实战记录.md]] 里踩过的坑（尤其是 `instance` 标签唯一性那个）。

## 前置：MySQL 这边先建一个最小权限的监控账号

不要用 root，参考官方 mysqld_exporter 的权限要求：

```sql
CREATE USER 'exporter'@'localhost' IDENTIFIED BY '换个强密码' WITH MAX_USER_CONNECTIONS 3;
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'localhost';
```

`MAX_USER_CONNECTIONS 3` 限制这个监控账号最多占用 3 个连接，防止 exporter 出问题时把数据库连接池打满。

## 密码不要明文写进配置文件

`prometheus.exporter.mysql` 的 `data_source_name` 参数是 **Secret 类型**（[[监控告警链路追踪/Alloy/Alloy 数据类型.md]] 讲过这个类型——Alloy 不会在 UI/日志里明文展示它）。用环境变量传密码，配合字符串拼接组出完整 DSN：

```bash
# /etc/default/alloy 或者 systemd override 里加（值要加双引号，见文末踩坑）
MYSQL_EXPORTER_PASSWORD="换个强密码"
```

```alloy
prometheus.exporter.mysql "default" {
  data_source_name = "exporter:" + sys.env("MYSQL_EXPORTER_PASSWORD") + "@(localhost:3306)/"
}
```

`sys.env()` 用法参考 [[监控告警链路追踪/Alloy/Alloy 函数调用.md]]，`+` 拼接字符串参考 [[监控告警链路追踪/Alloy/Alloy 运算符.md]]。

## 完整配置（database 机器，node + mysql 合并）

```alloy
logging {
  level = "warn"
}

// ---- node 指标 ----
prometheus.exporter.unix "default" {
  include_exporter_metrics = true
  disable_collectors       = ["mdadm"]
}

discovery.relabel "node_job" {
  targets = prometheus.exporter.unix.default.targets

  rule {
    target_label = "job"
    replacement  = "node"
  }

  rule {
    target_label = "instance"
    replacement  = constants.hostname
  }
}

// ---- mysql 指标 ----
prometheus.exporter.mysql "default" {
  data_source_name = "exporter:" + sys.env("MYSQL_EXPORTER_PASSWORD") + "@(localhost:3306)/"
}

discovery.relabel "mysql_job" {
  targets = prometheus.exporter.mysql.default.targets

  rule {
    target_label = "job"
    replacement  = "mysql"
  }

  rule {
    target_label = "instance"
    replacement  = constants.hostname
  }
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://192.168.31.1:9090/api/v1/write"
  }
}

prometheus.scrape "default" {
  targets = array.concat(
    discovery.relabel.node_job.output,
    discovery.relabel.mysql_job.output,
    [{
      job         = "alloy",
      __address__ = "127.0.0.1:12345",
    }],
  )

  forward_to = [prometheus.remote_write.default.receiver]
}
```

两组指标各自走独立的 `discovery.relabel`（`node_job`/`mysql_job`），`job` 分别设成 `node`/`mysql`，`instance` 统一用 `constants.hostname`（原生 systemd 装的，参考 [[监控告警链路追踪/Alloy/实践/Alloy 接入 Prometheus 实战记录.md]] 坑四的教训——**内嵌 exporter 一定要显式 relabel `instance`**，不然会落到 `__address__` 默认值，多台机器共用同一个值会导致 `out of order sample`）。最后 `prometheus.scrape` 用 `array.concat` 把两组 target 拼一起转发。

## 可选：只采部分 collector

`disable_collectors`/`enable_collectors`/`set_collectors` 三选一，控制采集范围：

```alloy
prometheus.exporter.mysql "default" {
  data_source_name  = "exporter:" + sys.env("MYSQL_EXPORTER_PASSWORD") + "@(localhost:3306)/"
  enable_collectors = ["info_schema.processlist", "info_schema.innodb_metrics"]
}
```

- `set_collectors`：完全覆盖默认集合，只跑你指定的
- `enable_collectors`：在默认集合基础上**加**
- `disable_collectors`：在默认集合基础上**减**

homelab 单机规模，默认集合就够用，不用特地精简。

## 卸载旧方案

参考 [[mysql部署prometheus]] 文末新增的"迁移到 Alloy 时的卸载步骤"，把 mysqld_exporter + node_exporter 都停掉卸干净，`prometheus.yml` 里对应这台机器的两条 `static_configs`（`job_name: 'node'` 和 `job_name: 'mysql'` 下各一条）也要删。

## 验证

跟 agent 那次一样三连：

```bash
# 1. Alloy 自己有没有把数据发出去
curl -s http://127.0.0.1:12345/metrics | grep prometheus_remote_storage_bytes_total

# 2. Prometheus 有没有收到 mysql 这个 job
curl -s http://192.168.31.1:9090/api/v1/label/job/values

# 3. instance 是不是正常机器名，不是 loopback 地址
curl -s http://192.168.31.1:9090/api/v1/label/instance/values

# 4. 具体指标查得到
curl -sg 'http://192.168.31.1:9090/api/v1/query?query=mysql_up'
```

`mysql_up` 这个指标本身就是 mysqld_exporter 自带的健康探测——能连上 MySQL 是 `1`，连不上是 `0`，比查具体业务指标更快确认链路通没通。

## 踩坑：`mysql_up=0` + `1045`，env 文件里的密码没加引号

现象：`mysql_up{job="mysql"}` 是 `0`，Alloy 日志每分钟一条：

```
Error 1045 (28000): Access denied for user 'exporter'@'localhost' (using password: YES)
```

`using password: YES` 说明密码送出去了，只是值不对，网络和授权的主机部分都没问题。原因和 PG 完全一样：`/etc/default/alloy` 里的 `MYSQL_EXPORTER_PASSWORD` **没加双引号**，密码里有特殊字符时被 systemd 解析成了别的值。加引号后 `systemctl restart alloy` 解决（**用 restart，不是 reload**）。

排查路径、判定方法、注意事项都在 [[监控告警链路追踪/Alloy/实践/Alloy 接入 PostgreSQL 指标.md]] 的"`pg_up=0` + `28P01`"一节，不重复写。

## 相关笔记

- [[监控告警链路追踪/Alloy/实践/Alloy 接入 PostgreSQL 指标.md]] — 同一台机器上的 PG，含同一个引号踩坑
- [[mysql部署prometheus]] — 旧方案 + 卸载步骤
- [[监控告警链路追踪/Alloy/实践/Alloy 接入 Prometheus 实战记录.md]] — node 指标实战 + `instance` 唯一性教训
- [[监控告警链路追踪/Alloy/Alloy 数据类型.md]] — Secret 类型
- [[监控告警链路追踪/Alloy/Alloy 函数调用.md]] — `sys.env()`
