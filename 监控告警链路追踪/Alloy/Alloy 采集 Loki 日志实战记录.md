---
publish: true
tags:
  - Alloy
  - Loki
  - homelab
cssclasses:
  - Alloy
---

把本机 systemd alloy 采集系统日志（syslog / auth.log / kern.log）和 Hermes 日志（`~/.hermes/logs/`）推到 docker-host Loki 的实战记录，对应 [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] 那篇 Loki 配方的实际落地。

## 最终结果

链路通：alloy → `http://192.168.31.1:3100/loki/api/v1/push` → docker-host Loki :3100。

验证（从 docker-host 本机 curl Loki API）：

```
curl http://127.0.0.1:3100/loki/api/v1/label/job/values
→ ["authlog", "docker", "hermes", "syslog"]

curl http://127.0.0.1:3100/loki/api/v1/label/host/values
→ ["agent", "docker-host"]

curl http://127.0.0.1:3100/loki/api/v1/label/log_type/values
→ ["agent", ...]
```

本机（agent）推过来的 job 有 `authlog` / `syslog` / `hermes`，host 一律 `agent`，Hermes 日志带 `log_type` 子分类。

## 最终配置

`/etc/alloy/config.alloy`（备份在 `.bak.2026-09-25-loki`）—— 在原 Prometheus 段后追加：

```alloy
// ============================================================
// Loki: system logs + Hermes logs -> remote_write
// ============================================================

// 系统日志：syslog / auth.log / kern.log
local.file_match "syslog" {
  path_targets = [
    {"__path__" = "/var/log/syslog",   "job" = "syslog",  "host" = "agent"},
    {"__path__" = "/var/log/auth.log", "job" = "authlog", "host" = "agent"},
    {"__path__" = "/var/log/kern.log", "job" = "kernlog", "host" = "agent"},
  ]
  sync_period = "5s"
}

loki.source.file "syslog" {
  targets       = local.file_match.syslog.targets
  forward_to    = [loki.process.add_labels.receiver]
  tail_from_end = true
}

// Hermes 日志：~/.hermes/logs/*.log
local.file_match "hermes_logs" {
  path_targets = [
    {"__path__" = "/root/.hermes/logs/agent.log",        "job" = "hermes", "log_type" = "agent",     "host" = "agent"},
    {"__path__" = "/root/.hermes/logs/errors.log",        "job" = "hermes", "log_type" = "errors",    "host" = "agent"},
    {"__path__" = "/root/.hermes/logs/gateway.log",      "job" = "hermes", "log_type" = "gateway",   "host" = "agent"},
    {"__path__" = "/root/.hermes/logs/gui.log",          "job" = "hermes", "log_type" = "gui",       "host" = "agent"},
    {"__path__" = "/root/.hermes/logs/update.log",       "job" = "hermes", "log_type" = "update",    "host" = "agent"},
    {"__path__" = "/root/.hermes/logs/dashboard-auth.log","job" = "hermes", "log_type" = "dashboard", "host" = "agent"},
  ]
  sync_period = "5s"
}

loki.source.file "hermes" {
  targets       = local.file_match.hermes_logs.targets
  forward_to    = [loki.process.add_labels.receiver]
  tail_from_end = true
}

// 统一打 cluster 标签后转发
loki.process "add_labels" {
  forward_to = [loki.write.local.receiver]

  stage.static_labels {
    values = {
      cluster = "homelab",
    }
  }
}

loki.write "local" {
  endpoint {
    url = "http://192.168.31.1:3100/loki/api/v1/push"
  }
}
```

## 系统层改动（权限 + systemd override）

**关键约束**：alloy 以 `alloy` 用户（uid=999，主组 `adm`+`systemd-journal`）跑，但 `/root`、`/root/.hermes`、`/root/.hermes/logs` 三个目录原本都是 `700 root:root` ——alloy 用户**目录都进不去**。

按"最小权限"原则三层放开：

```bash
chmod 751 /root              # root 有 rwx，其他只有 x（可 traverse、不见 ls）
chmod 755 /root/.hermes       # 可 traverse、可见目录列表
chmod 755 /root/.hermes/logs  # 文件本身 644 root:root 不动
```

**`751` 是关键**——比 `755` 紧一层：root 用户仍能 `ls /root`，但 alloy 用户**不能**看 `/root` 下的目录列表（无 r 位），只能 traverse 到已知路径。这是 Linux 文件权限的标准做法——open by name 时每级目录都要 x 位，但目录列表只在 owner / group 范围内可见。

systemd 单元用 override 文件持久化（不要直接改 `/lib/systemd/system/alloy.service`，那是 apt 包管理的路径，下次升级会被覆盖）：

```bash
mkdir -p /etc/systemd/system/alloy.service.d
cat > /etc/systemd/system/alloy.service.d/override.conf <<'EOF'
[Service]
ReadOnlyPaths=/root/.hermes/logs
EOF
systemctl daemon-reload
```

`ReadOnlyPaths` 限定 alloy 文件系统访问范围只在 `/root/.hermes/logs` 下——即便以后扩大 `/root` 权限，alloy 进程也无法越权读其他文件。

## 诊断信号对照

| 看什么 | 含义 |
| --- | --- |
| `loki_source_file_files_active_total{component_id="loki.source.file.hermes"}` | Hermes 6 个文件都打开成功 |
| `loki_source_file_files_active_total{component_id="loki.source.file.syslog"}` | 系统日志 3 个文件都打开成功 |
| `loki_source_file_read_bytes_total{path="..."}` 增长 | alloy 在 tail 文件 |
| `loki_write_sent_entries_total{host="192.168.31.1:3100"}` 增长 | batch 真发出去被 Loki 接收 |
| `loki_write_dropped_entries_total{reason="line_too_long"\|"rate_limited"\|"stream_limited"}` | 各类失败原因 |
| Loki `/api/v1/label/job/values` 含 `hermes` `authlog` `syslog` | 端到端通 |

`tail_from_end = true` 启动时**只采新行**，不读历史——重启 alloy 后已落盘的日志不会回灌。如果要回灌历史改 `tail_from_end = false`（谨慎，可能瞬间灌巨量数据）。

## 没采的日志（备忘）

`/root/.hermes/logs/` 下还有几类日志**这次没采**，因为它们是事件型（只在异常时出现）或者 rotated 历史：

- `gateway-shutdown-diag.log` / `gateway-exit-diag.log` / `gateway_faulthandler.log` —— gateway 异常退出诊断
- `tui_gateway_crash.log` —— TUI 客户端崩溃
- `agent.log.{1,2,3}` —— rotated 历史 agent.log

要采的话在 `local.file_match.hermes_logs.path_targets` 里加对应 `__path__` 条目。注意 Loki 默认单 stream 标签基数有限，**不要用 rotated 时间戳做 label**（会爆 stream 数）。

## 跟 [[监控告警链路追踪/Alloy/Alloy 接入 Prometheus 实战记录.md]] 的关系

那篇是 Prometheus 指标链路（Prometheus ↔ unix_exporter + alloy 自指），这篇是 Loki 日志链路（alloy → Loki）。同一份 alloy config 既推 Prom 也推 Loki，互不影响。两篇共用同一份 `systemctl restart alloy` 节奏。

## 下一步

- [ ] Loki 端确认 retention / ingest rate（homelab 量级默认够用，但要查 `loki_write_sent_entries_total` 持续涨的速度）
- [ ] Grafana 加 Loki 数据源（如果还没加），配 `job=hermes` 等 dashboard
- [ ] `tail_from_end=true` 改成 `false` 回灌历史（先评估 Loki 容量）
- [ ] Hermes rotated 历史 `agent.log.{1,2,3}` 是否要采，看存储意愿

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] — Loki 部分配方来源
- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — Pipeline 模式
- [[监控告警链路追踪/Alloy/Alloy 接入 Prometheus 实战记录.md]] — 同一 alloy 实例的 Prom 链路实战
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — Alloy 整体