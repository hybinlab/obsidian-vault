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
- exporter 嵌在 Alloy 进程里，只通过 `localhost:5432` 连本机 PostgreSQL，不会额外开监听端口（**没有 9187**，见下文踩坑），暴露面已经很小

## 凭据注入

跟 MySQL 同套路：密码走 systemd EnvironmentFile 注入，alloy 配置里 `sys.env()` 取值。

```bash
# /etc/default/alloy 追加（值一定要加双引号，见下文踩坑）
POSTGRES_EXPORTER_PASSWORD="postgres超级用户密码"
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

### reload 通过不等于连得通，也不能用 `ss | grep 9187` 判断

reload 通过只说明配置语法没错。如果密码不对，exporter 会一直刷 `pq: password authentication failed`，但组件**仍在跑**，只是 scrape 拿不到样本。

**`prometheus.exporter.postgres` 是嵌在 Alloy 进程里的，不会单独监听 9187**（和 `prometheus.exporter.unix` 一样，指标通过 Alloy 自己的 12345 端口暴露；没有实测这一个组件，依据是 unix exporter 的 `instance` 默认落到 `127.0.0.1:12345`）。所以 `ss -ltnp | grep 9187` 没输出是正常的，它既不能证明通，也不能证明不通。正确的判断方法：

```bash
# Prometheus 端：1 = 通，0 = 采集在跑但连不上库，空 = 数据没送到
curl -s 'http://192.168.31.1:9090/api/v1/query?query=pg_up' | jq .
# Alloy 端：看具体报错
journalctl -u alloy --since "10 min ago" --no-pager | grep -iE "postgres|pq:"
```

### `pg_up=0` + `28P01`：`/etc/default/alloy` 里的密码没加引号

现象：`pg_up{job="postgres"}` 是 `0`，Alloy 日志每分钟一条：

```
pq: password authentication failed for user "postgres" (28P01)
```

这个报错出在**密码校验这一步**，说明连接已经到达库，网络、`pg_hba.conf` 都不是问题，是 Alloy 送出去的密码和库里的不一致。实际原因：**env 文件里的值没加引号**。密码含特殊字符时，systemd 读取 `EnvironmentFile` 会把值解析成别的内容，Alloy 拿到的就不是设置的那个密码。给值加双引号后 `systemctl restart alloy` 解决。

- 具体是哪个字符被改写，取决于密码内容。systemd 对各字符的解析规则我没有逐条核对，以 `systemd.exec(5)` 的 `EnvironmentFile=` 一节为准。密码里尽量避免 `\`、`"`、`#`、空格
- **改完 env 文件要 `systemctl restart alloy`，reload 不会重新读环境变量**（环境变量是进程启动时读进去的）
- 排查时可以用这条判定 Alloy 手里的密码对不对（**不打印到屏幕**）；本次是直接加引号重启解决的，这条没有实际跑过：

```bash
PW=$(tr '\0' '\n' < /proc/$(systemctl show -p MainPID --value alloy)/environ | grep '^POSTGRES_EXPORTER_PASSWORD=' | cut -d= -f2-)
PGPASSWORD="$PW" psql -h localhost -U postgres -d postgres -c 'select 1'
```

MySQL 是同一个原因，见 [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]]。

## 备份

本次改动前的版本留在 `/etc/alloy/config.alloy.bak.2026-09-28`，env 文件备份在 `/etc/default/alloy.bak.2026-09-28`。

## 验证

```bash
# 1. alloy 进程收到了这个环境变量（只看有没有，不把密码打印出来）
cat /proc/$(systemctl show -p MainPID --value alloy)/environ | tr '\0' '\n' | grep '^POSTGRES' | sed 's/=.*/=<已设置>/'

# 2. Prom 端有 postgres job 数据，值必须是 1
curl -s 'http://192.168.31.1:9090/api/v1/query?query=pg_up{job="postgres"}' | jq .
```

（原来的"exporter 监听 9187"这一步已删除，嵌入式 exporter 没有这个端口，见上文。）

## 面板

Grafana 面板 ID `9628`（"PostgreSQL Database"，适配 `postgres_exporter`）。导入后 `Instance` 选 `database` 直接有数据（`instance` 标签在 relabel 里设成了 hostname）。顶部 `Namespace`、`Release` 两个下拉框是空的，不影响使用。

## 遗留

- 长期要把 `postgres` 超级用户换成专用 `pg_exporter` 角色（最小权限）
- [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]] 同款问题：`/etc/default/alloy` 文件权限 644，明文密码——跟 USER PROFILE 红线冲突，**先跑通**妥协
- ~~MySQL exporter 仍在报 1045~~：已解决，和 PG 是同一个原因（env 文件里的密码没加引号），见 [[监控告警链路追踪/Alloy/实践/Alloy 接入 MySQL 指标.md]]