---
publish: true
tags:
  - Alloy
  - Loki
  - homelab
cssclasses:
  - Alloy
---

把本机 systemd alloy 采集系统日志（syslog / auth.log / kern.log）、Hermes 日志（`~/.hermes/logs/`）和 Hindsight 日志（`/var/log/hindsight/`）推到 docker-host Loki 的实战记录，对应 [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] 那篇 Loki 配方的实际落地。

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

后续加了 `job="hindsight"`（见下文"Hindsight 日志"一节），它比其他几个多两个由解析阶段提出来的标签 `level`、`logger`，外加区分 stdout/stderr 的 `stream`。这一条上线后的 curl 输出我没有记，验证方法同上：`label/job/values` 里应出现 `hindsight`。

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

// ============================================================
// Hindsight 日志：/var/log/hindsight/*.log（systemd append: 输出）
// ============================================================

local.file_match "hindsight_logs" {
  path_targets = [
    {"__path__" = "/var/log/hindsight/hindsight.log",     "job" = "hindsight", "stream" = "stdout", "host" = "agent"},
    {"__path__" = "/var/log/hindsight/hindsight.err.log", "job" = "hindsight", "stream" = "stderr", "host" = "agent"},
  ]
  sync_period = "5s"
}

loki.source.file "hindsight" {
  targets       = local.file_match.hindsight_logs.targets
  forward_to    = [loki.process.hindsight_parse.receiver]
  tail_from_end = true
}

// 解析 "2026-09-29 10:39:53,406 - INFO - logger.name - message" 格式
loki.process "hindsight_parse" {
  forward_to = [loki.write.local.receiver]

  // Python 默认 logging 格式：ts - LEVEL - logger - message
  stage.regex {
    expression = "^(?P<py_ts>\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}[,\\.]\\d+)\\s+-\\s+(?P<level>[A-Z]+)\\s+-\\s+(?P<logger>[^\\s]+)\\s+-\\s+(?P<msg>.*)$"
  }

  stage.labels {
    values = {
      level  = "level",
      logger = "logger",
    }
  }

  stage.output {
    source = "msg"
  }

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

## Hindsight 日志：Python logging → 解析成标签

Hindsight API 是 Python 服务（部署见 [[homelab/AI Agent/Hermes + Hindsight 部署 SOP.md]]），日志由 systemd 的 `append:` 输出写进 `/var/log/hindsight/`：stdout → `hindsight.log`，stderr → `hindsight.err.log`，分别打上 `stream=stdout` / `stream=stderr`。

这条链路比系统日志/Hermes 多一步解析（`loki.process "hindsight_parse"`），日志格式是 Python logging 默认的 `时间 - 级别 - logger - 正文`：

1. `stage.regex`：用命名捕获组抽出 `py_ts` / `level` / `logger` / `msg`，进"提取映射表"（机制见 [[Alloy 处理日志（多阶段 Pipeline）]]）
2. `stage.labels`：把 `level`、`logger` 提成 Loki 标签，之后能直接 `{job="hindsight", level="ERROR"}` 筛
3. `stage.output`：日志正文换成只剩 `msg`——级别和 logger 已经在标签里了，正文里不重复存
4. `stage.static_labels`：补 `cluster="homelab"`

`hindsight_parse` 直接转发到 `loki.write`，没有经过 `add_labels`，所以 `cluster` 在这里又写了一遍。改成 `forward_to = [loki.process.add_labels.receiver]` 并删掉这里的 `stage.static_labels`，效果等价、少一处重复。

### 已知局限（都没改，先记着）

**1. 原始时间戳没用上。** `py_ts` 抽出来了，但没接 `stage.timestamp`。文档写明：没配这个 stage 时，`loki.process` 保持上游附加的时间戳，也就是 Alloy 读到这行的时间。配合 `tail_from_end = true` 只读新行，两者差几秒，实际无影响。要用原始时间的话得加 `stage.timestamp`，而 Python 的 asctime 不带时区，需要显式写 `location = "Asia/Shanghai"`（文档：`location` 为 IANA 时区名，决定时间值按哪个时区解释）。

**2. Python traceback 会被拆成很多条。** 只有第一行符合 `时间 - 级别 - logger - 正文` 格式，`Traceback ...` 后面的续行不符合。`loki.process` 里没有 `stage.multiline`，续行就各自成为独立的 Loki 条目。这是 Python 服务最有价值的日志，被拆散后很难按一次异常回看。

- `stage.regex` 和 `stage.output` 遇到不匹配的行怎么处理，文档没写。Promtail 同源实现是原样透传（未验证）；如果属实，续行会作为不带 `level`/`logger` 标签的另一条流出现。验证方法：Explore 里查 `{job="hindsight"}`，看有没有不带 `level` 标签的行
- 可选修法：在 `hindsight_parse` 里最前面加 `stage.multiline`，文档参数为 `firstline`（必填）、`max_wait_time`（默认 3s）、`max_lines`（默认 128），应放在需要合并的最前面，例如：

```alloy
  stage.multiline {
    firstline     = "^\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}"
    max_wait_time = "3s"
  }
```

  注意副作用：**凡是不匹配 `firstline` 的行都会被并进上一条**。Hindsight 用 uvicorn，它自己的启动行是 `INFO:     Started server process` 这种不带时间戳的格式，会被粘到上一条日志后面。上线前得对着真实日志调 `firstline`，这段我没在真实数据上测过，所以没放进上面的"最终配置"。

**3. `logger` 做标签的基数。** 只要 logger 名按模块命名，数量有限，没问题。如果代码里按请求或租户动态起 logger 名，stream 数会爆。抽查一下：

```bash
curl -s http://127.0.0.1:3100/loki/api/v1/label/logger/values
```

**4. 日志文件会一直长大。** systemd 的 `append:` 只负责追加，不轮转。需要配 logrotate；因为 systemd 一直持有文件句柄，用 `copytruncate`，别用 rename + create（否则 systemd 会继续写进被改名的旧文件）。目前我没看到这份 logrotate 配置。

**5. `journalctl -u hindsight` 已经看不到应用输出。** unit 里 `StandardOutput` / `StandardError` 是 `append:`（已确认），应用日志只在 `/var/log/hindsight/` 的文件里，journal 里只剩 systemd 自己的启停记录。[[homelab/AI Agent/Hermes + Hindsight 部署 SOP.md]] 的 §10 / §11 / §13 已按这份 unit 同步，其中还补了 logrotate 建议（尚未配置）。

## 诊断信号对照

| 看什么 | 含义 |
| --- | --- |
| `loki_source_file_files_active_total{component_id="loki.source.file.hindsight"}` | Hindsight 两个文件（stdout/stderr）都打开成功，期望值 2 |
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

## 多机对齐：homelab 集群标签

homelab 集群里两台机器都在推 Loki，标签体系要统一：

| 维度 | 本机 (agent, systemd alloy) | docker-host (容器 alloy) |
|---|---|---|
| **hostname** | `agent` | `docker-host` |
| **host label** | `"agent"`（硬编码，跟 hostname 一致） | `"docker-host"`（硬编码，跟 hostname 一致）|
| **cluster label** | `cluster = "homelab"`（`loki.process add_labels`） | `cluster = "homelab"`（同一套）|
| **job** | syslog / authlog / kernlog / hermes / hindsight | docker / syslog / authlog |

docker-host 上原来的 `config.alloy` **没有 `cluster` 标签**，只给本机加了之后 Loki 端筛 `{cluster="homelab"}` 会漏掉 docker-host 的日志。补齐那台需要做：

1. 备份：`ssh docker-host 'cp /root/monitoring/config.alloy /root/monitoring/config.alloy.bak.<date>'`
2. 在 `loki.write` 段之前插入 `loki.process "add_labels"` 段（结构跟本机一样，`cluster = "homelab"`、`forward_to = [loki.write.local.receiver]`）
3. `loki.source.file "syslog"` 的 `forward_to` 改成 `[loki.process.add_labels.receiver]`。docker 那条**不能直接改**，要串起来：`loki.source.docker` → `loki.process "docker_logs"`（打 `job="docker"`）→ `loki.process "add_labels"`（打 `cluster`），即 `loki.source.docker` 转给 `docker_logs`，`docker_logs` 再转给 `add_labels`。如果把 `loki.source.docker` 直接转给 `add_labels`，会绕过 `docker_logs`，容器日志就丢了 `job="docker"`（实际发生过，Loki 日志里能看到流标签里没有 `job`）
4. 容器没有 curl/wget，**热加载靠 `docker compose restart alloy`**（容器 alloy 不支持 `/-/reload` 因为 exec 没 HTTP 工具；这是 docker 镜像精简过的代价）

验证：

```
curl http://127.0.0.1:3100/loki/api/v1/label/cluster/values
→ ["homelab"]
```

跑完两台机器所有 Loki 日志都贴 `cluster="homelab"`，按集群筛干净。

**`/etc/hostname` 是这两台机器 host label 的真实来源**——目前是硬编码到 alloy 配置里，如果机器改名 / 搬网段要同步改。也可以用 `loki.process.stage.template` + `local.file_match` 读 `/etc/hostname` 动态注入，但 homelab 规模不值得。

## 跟 [[监控告警链路追踪/Alloy/Alloy 接入 Prometheus 实战记录.md]] 的关系

那篇是 Prometheus 指标链路（Prometheus ↔ unix_exporter + alloy 自指），这篇是 Loki 日志链路（alloy → Loki）。同一份 alloy config 既推 Prom 也推 Loki，互不影响。两篇共用同一份 `systemctl restart alloy` 节奏。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] — Loki 部分配方来源
- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — Pipeline 模式
- [[监控告警链路追踪/Alloy/Alloy 接入 Prometheus 实战记录.md]] — 同一 alloy 实例的 Prom 链路实战
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — Alloy 整体
- [[Alloy 处理日志（多阶段 Pipeline）]] — `loki.process` 各 stage 与提取映射表
- [[homelab/AI Agent/Hermes + Hindsight 部署 SOP.md]] — Hindsight 服务本身的部署
- [[Loki 日志告警与监控组件自监控]] — 基于这里采集的日志做告警（agent 断流会触发 LogIngestionStopped）