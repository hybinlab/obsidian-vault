---
publish: true
tags:
  - homelab
  - Hermes
  - 告警
---

> 2026-11-03 接入。Hermes 在 agent 本机 `/root/.hermes`，由 user systemd 的 `hermes-gateway.service` 管理。本机源码提交为 `db39ee3f28`。
> 2026-11-23 扩展：全部 critical + 现有 20 类 warning；补充时间戳、日志来源和 Loki 告警核验要求。配置已重载，当前覆盖 34 类故障告警。
> Webhook 的通用配置、动态路由热加载及 Session 行为见 [[Webhooks（事件触发与消息投递）]]。

## 目标与链路

Alertmanager 收到指定告警后，同时发送原始 ntfy 通知，并触发 Hermes 查询指标、日志和主机清单，随后将诊断结果投递到已连接的微信会话。初次接入用 ntfy 验证，之后诊断路由已改为 `deliver: weixin`。

```text
Prometheus / Loki ruler → Alertmanager
  ├─ 原有 ntfy webhook → homelab-alerts → 手机
  └─ agent:8644/webhooks/homelab-alerts
       → 过滤 → 同组事件合并 → Hermes 只读诊断
       → Gateway 微信渠道 → 用户微信
```

2026-11-03 首批接入 `NodeDown`、`RemoteWriteStale`、`ContainerRestartLoop`、`ContainerOOMKilled`；2026-11-23 已扩展为下述范围。组合 receiver `ntfy-hermes` 复制原 `ntfy` receiver，并增加 Hermes webhook；恢复通知仍由 ntfy 发送，Hermes 分支设置 `send_resolved: false`。

## 当前覆盖范围与路由

| 范围 | 行为 |
|---|---|
| `Watchdog` | 最先匹配 `null` receiver，不触发 Hermes；即使以后误标为 critical 也排除 |
| 全部 `severity="critical"` | 进入 `ntfy-hermes`，以后新增 critical 自动覆盖 |
| `severity="warning"` 且名称在下表 | 进入 `ntfy-hermes`，以后新增 warning 需显式加入白名单 |
| 其他 severity、无 severity、未列入的 warning | 沿用默认 `ntfy` receiver |
| 恢复事件 | Hermes webhook 不发送恢复事件，过滤脚本也会忽略；原始恢复通知仍走 ntfy |

Warning 白名单共 20 类：

| 类别 | 告警名称 |
|---|---|
| 主机磁盘 | `DiskSpaceLow`、`DiskWillFillIn24h`、`InodesLow` |
| 主机内存与负载 | `MemoryLow`、`OOMKill`、`CPUHigh`、`LoadHigh` |
| 容器 | `ContainerOOMKilled`、`ContainerMemoryNearLimit`、`ContainerDisappeared`、`ContainerErrorSpike` |
| 监控与日志组件 | `BlackboxDown`、`CAdvisorDown`、`GrafanaDown`、`AlloyDroppingLogs`、`LokiRuleEvaluationFailing`、`PrometheusRuleEvaluationFailing` |
| 证书、隧道与 SSH | `NtfyCertExpiringSoon`、`FrpcReconnecting`、`SSHBruteForce` |

实查 Prometheus 29 类、Loki 6 类，共 35 类告警；排除 Watchdog 后，现有 14 类 critical 和 20 类 warning 均已接入。`DiskIOError`、`SSHLoginFromOutside`、`LogIngestionStopped` 等日志类 critical 通过 severity 规则覆盖，无需单独列出。

脱敏的路由片段见 `hermes-alerts/alertmanager-routes.yml`，只用于合并现有 `route`，不能当作完整 Alertmanager 配置覆盖。保留原 `receivers`、凭据及其他配置；Watchdog 排除规则必须位于 Hermes 规则之前。两条 Hermes 路由均在匹配后停止，组合 receiver 本身已包含 ntfy，无需 `continue: true` 重复投递。

此次保持 `group_by: [alertname, instance]`、`group_wait: 30s`、`group_interval: 5m`、`repeat_interval: 4h`。不同告警名称或实例仍是不同组，不会因扩展覆盖自动合并成同一次诊断。

## 实际配置

| 位置 | 内容 |
|---|---|
| agent `/root/.hermes/config.yaml` | Webhook、诊断 prompt、按平台及路由限制工具 |
| agent `/root/.hermes/.env` | ntfy 地址、独立账号 token、输出 topic；权限 0600 |
| agent `/root/.hermes/plugins/homelab-alerts/` | 本地只读查询插件 |
| agent `/root/.hermes/scripts/homelab_alert_filter.py` | 告警过滤、字段与长度限制 |
| docker-host `/root/monitoring/alertmanager.yml` | `ntfy-hermes` receiver、critical 路由与 warning 白名单路由 |
| ntfy 账号 `hermes-alerts` | 正式 topic 只写；独立 inbox 只读；测试 topic 读写 |

支持文件保存在本笔记旁的 `hermes-alerts/`：`plugin.yaml`、`__init__.py`、`filter_alert.py`、`diagnostic_prompt.txt`、`alertmanager-routes.yml`。插件与过滤脚本运行时使用复制到 `.hermes` 下的版本，修改知识库源码后需同步再重载。`diagnostic_prompt.txt` 对应 `config.yaml` 的 `platforms.webhook.extra.routes.homelab-alerts.prompt`，路由片段对应 docker-host 的 Alertmanager 配置；这两个文件不会被服务自动读取。

Webhook 只监听内网 `192.168.31.4:8644`，未配置 ECS/FRP 公网入口。Alertmanager 0.34.1 支持 `http_config.http_headers`，本机 Hermes 验证逻辑接受 `X-Gitlab-Token` 与路由 secret 比较，因此可以直接对接，不需要额外签名桥。

```yaml
# 节选；所有凭据均为占位符，不能直接照此覆盖完整配置。
webhook_configs:
  - url: http://192.168.31.4:8644/webhooks/homelab-alerts
    send_resolved: false
    timeout: 10s
    http_config:
      http_headers:
        X-Gitlab-Token:
          secrets: ["<随机路由 secret>"]
```

静态 Token 通过内网 HTTP 传输；该模式不提供 HMAC 的请求体完整性校验。以后如果跨不可信网络，应配置 TLS 或改用带时间戳的 HMAC。

## 只读范围与事件控制

实际解析出的业务工具集仅为 `homelab_observe`，并设置 `no_mcp`，排除其他插件工具集。Hermes 仍可能使用内部工具发现包装器；这些包装器只能调用当前会话已授权的工具。

- `inventory`：读取固定路径的 `01-主机清单.md`。
- `prometheus`：仅访问固定的 Prometheus instant-query API，服务端查询超时 5 秒。
- `logs`：仅访问固定的 Loki query-range API，窗口 1–60 分钟、最多 60 行。
- 无 Shell、SSH、任意文件路径、任意 URL 或基础设施写操作；HTTP 跳转禁用，输出受大小限制。
- 本次 Gateway 日志确认，`memory` 工具集被关闭后 Hindsight 工具和记忆 prompt 均未注入诊断会话。

Webhook 路由每分钟最多 12 个请求，请求体上限 128 KiB。脚本忽略恢复事件和 Watchdog，每组最多向 prompt 提供 8 条告警。同一个 `groupKey` 在安静 30 秒后合并执行，最多等待 120 秒；它不是持久队列，也不合并不同组的任务。

Alertmanager 的重发间隔为 4 小时，持续故障可能再次诊断。Hermes 的 delivery-ID 去重仅在发送方提供稳定 ID 时才有相应保障；不能把事件合并当成跨重试的严格幂等性。

诊断 prompt 要求证据与推断分开；查询不到 `ALERTS` 不能直接认定恢复，时间相邻不能证明因果。最多 6 次查询是 prompt 中的建议，未作为硬性执行预算；验收时模型曾超过这一建议。

2026-11-23 根据 [[2026-11-23-remotewrite-stale-clock-skew]] 补充诊断要求：

- 指标为空时读取原始范围向量，对照原始样本时间戳与 Prometheus 查询时间；不能用 `timestamp(last_over_time(...))` 计算原始样本年龄。
- 其他主机的远程写错误只能作为线索，不能直接归因到告警主机；容器名也不能直接当宿主机名。
- 按实际主机、容器和 job 缩小日志查询，达到 60 行或截断不能证明没有目标日志。
- Loki 告警可能不在 Prometheus 的 `ALERTS` 中，应核对对应 LogQL 日志或计数；资源、证书、探测和通知链路告警分别查对应指标。
- 没有 SSH、systemd 或主动网络探测能力，未取得的本机状态必须列为未验证；报告中的建议不能写成已经执行。

## 微信出口与 ntfy 验收记录

当前诊断路由使用 `deliver: weixin`，投递到微信渠道的默认 home channel。模型只负责输出最终报告，发送由 Gateway 完成，不需要模型寻找或调用发送消息的工具。诊断 prompt 已明确这一规则；首次微信测试曾因模型反复寻找发送工具而延迟。

2026-11-03 微信验收：模拟事件触发 Hermes 并生成最终文本；微信接口首次返回 `ret=-2 / session not ready`。用户激活微信会话后，收到了带 `Recovered reply` 标记的补发消息，用户确认成功。该记录验证了本次重连后的补投递，不代表长期空闲会话下的首次主动投递已验证；补发也可能产生重复消息。

初次接入时启用了官方内置 `ntfy-platform` 插件，先向 `hermes-diagnostics-test` 发送模拟诊断，再切到 `homelab-alerts`。该插件及独立账号仍保留；原始告警继续由 Alertmanager 直接推送 ntfy。

本机版本的 ntfy 适配器优先使用 `NTFY_PUBLISH_TOPIC`，不能假定 Webhook 的 `deliver_extra.chat_id` 可以覆盖它。测试时将 publish/home channel 指向 `hermes-diagnostics-test`，验证后再切回正式 topic。重载 Gateway 也可能向 home channel 发送上线通知，它不等于诊断成功。

## 验证记录

2026-11-03 已完成：

- Hermes 官方插件 validator 全部通过；恢复事件、Watchdog、字段截断及非法查询类型验证通过。
- 实际平台工具集解析只包含 `homelab_observe`，无 MCP/Shell 工具。
- Prometheus、Loki 的实际查询成功。
- 无 Token 请求返回 401；有效 Token 的空事件返回 ignored，不启动诊断。
- 模拟 Webhook 经 30 秒合并窗口触发 Hermes，实际调用查询工具，约 85 秒完成推理，最终报告到达测试 topic。已区分 Gateway 上线通知和真正的诊断报告。
- 正式接入前，从 docker-host 验证了带 Token 的空事件请求；Alertmanager 配置经 `amtool check-config` 后重载。
- 微信验收消息 `HermesWeixinDeliveryTest` 已由用户确认收到；首次发送失败，渠道恢复后自动补发成功。此轮重试只验证事件触发、模型生成和微信投递，指标/日志查询已在此前验收中验证。

验收未向 Alertmanager 注入虚构生产告警；真实告警经 Alertmanager 自动触发的后续表现仍需观察。

2026-11-23 扩展覆盖已完成：

- 用 `amtool check-config` 校验候选配置及正式文件；35 条现有规则逐条通过路由测试。
- 额外验证未来 critical → `ntfy-hermes`、未来未列入 warning → `ntfy`、info 测试告警 → `ntfy`、即使标为 critical 的 Watchdog → `null`。
- Alertmanager 已通过 `/-/reload` 重载，读取 `/api/v2/status` 确认实际加载的匹配器和预期一致；比较匹配器时忽略显示顺序。
- 过滤脚本验证新增 warning/critical 可通过，Watchdog 和 resolved 被忽略；脚本本身无须修改。
- 诊断 prompt 已同步并平滑重载 Hermes，运行时文本与知识库文件一致，原工具限制和微信出口保持原值；Gateway 为 active/running，`/health` 返回 HTTP 200。
- 验证时实际只有 Watchdog，没有向生产注入测试告警，也未发送模拟诊断。因此新增类别的完整诊断与微信投递仍待后续真实告警验证。

可复用的路由验证命令（docker-host）：

```bash
docker exec alertmanager /bin/amtool config routes test \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --verify.receivers=ntfy-hermes alertname=DiskSpaceLow severity=warning

docker exec alertmanager /bin/amtool config routes test \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --verify.receivers=null alertname=Watchdog severity=critical
```

## 运维与回退

```bash
# agent
systemctl --user status hermes-gateway.service
curl -s http://192.168.31.4:8644/health
# 修改配置或同步插件后平滑重载
systemctl --user reload hermes-gateway.service

# docker-host：先校验，再重载
docker exec alertmanager /bin/amtool check-config /etc/alertmanager/alertmanager.yml
curl -X POST http://127.0.0.1:9093/-/reload
```

Gateway 日志在 `/root/.hermes/logs/gateway.log`，模型及工具执行记录在 `agent.log`。不要直接把含 Token 的完整配置或 `.env` 贴入日志、笔记或聊天。

备份：

- Hermes 接入前：`/root/.hermes/backups/homelab-alerts-20261103-203708/`。
- Hermes 正式启用前：`/root/.hermes/backups/homelab-alerts-activate-20261103-204603/`。
- Alertmanager 接入前：`/root/monitoring/alertmanager.yml.bak.hermes-20261103-204619`。
- 2026-11-23 扩展前的 Hermes 配置：agent `/root/.hermes/backups/homelab-alerts-coverage-20261123-222210/config.yaml`。
- 2026-11-23 扩展前的 Alertmanager 配置：docker-host `/root/monitoring/backups/hermes-coverage-20261123-222325/alertmanager.yml`。

仅回退此次扩展时，将上述 Alertmanager 备份中的原四类匹配器恢复到当前路由，校验并重载；若之后没有其他配置改动，也可恢复该备份文件。prompt 可从对应 Hermes 备份中取回旧值并重载 Gateway。恢复前先核对后续变更，避免覆盖新配置。

暂停自动诊断时，先移除 Alertmanager 指向 `ntfy-hermes` 的子路由，使告警回到原有 `ntfy` receiver，校验并重载。完全回退时再恢复 Hermes 接入前的 `config.yaml`、`.env`，重载 Gateway；相关插件文件可以保留为未启用状态。恢复整份备份前先确认没有需要保留的后续配置改动。

参考：[Hermes Webhooks](https://hermes-agent.nousresearch.com/docs/zh-Hans/user-guide/messaging/webhooks)、[[Prometheus 告警 → ntfy 手机推送]]。
