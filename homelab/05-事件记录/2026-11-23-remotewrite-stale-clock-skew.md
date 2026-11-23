---
publish: true
tags:
  - homelab
  - 事件记录
  - 监控
  - NTP
---

| 项目 | 内容 |
|---|---|
| 时间 | 2026-11-23；18:20 的 Hermes 报告显示告警仍在 firing，当晚排查并由用户修复 |
| 现象 | `RemoteWriteStale` 在 middleware 上持续触发；即时查询看不到该机的 `up` 和 `node_*`，但 Alloy 正常运行 |
| 影响 | middleware 主机指标在当前查询和面板中不可见；Redis 容器运行中，未验证业务功能 |
| 直接原因 | middleware 与 Prometheus 所在 docker-host 存在约 5 分 40 秒的时钟偏差，样本时间戳落在接收端最近 5 分钟窗口之外 |
| 时间同步问题 | 两台均为 `Asia/Shanghai`，但 `NTPSynchronized=no`；默认 `ntp.ubuntu.com` 有多次超时记录。具体网络原因未查明，不能据此断定是代理问题 |
| 处理 | 用户直接修改已有 `/etc/systemd/timesyncd.conf` 的时间源配置，随后确认问题解决；不新增 drop-in 配置文件 |
| 验证边界 | 修复前的状态、指标和日志已实查；修复后由用户确认解决，未再次远程采集同步状态及告警恢复证据 |

相关：[[Ansible 批量部署 Alloy 实战记录]]、[[Hermes 告警诊断 Webhook 接入 SOP]]、[[2026-10-06-middleware-nodedown]]。

## 为什么会表现为“监控断流”

middleware 用 Alloy 内置的 Unix exporter 采集主机指标，再 remote write 给 Prometheus，并不依赖单独安装的 node_exporter。

发送端的系统时钟决定样本时间戳，接收端的时钟决定查询时点。例如 Prometheus 认为现在是 22:00，middleware 刚采集的指标却标着 21:54，那么这条数据即使刚刚成功入库，也不在“最近 5 分钟”内。

当时的规则为：

```yaml
- alert: RemoteWriteStale
  expr: absent_over_time(up{job="node", instance="middleware"}[5m])
  for: 2m
```

规则每 30 秒评估一次。在时间戳持续落后超过窗口的情况下，规则看到的是最近 5 分钟没有样本，持续 2 分钟后进入 firing。普通即时查询的默认回看窗口也是 5 分钟，所以 `up` 和 `node_*` 看起来会一起消失。

本次数据仍在入库。**即时查询为空，只能说明当前查询没有选中样本，不能直接证明采集停止或写入失败。**

## 关键证据与误判纠正

| 实查证据 | 含义 |
|---|---|
| middleware 可 SSH，根分区使用率 18% | 排除当时主机不可达和根分区满 |
| Alloy 为 active/running，从 11 月 14 日持续运行，`NRestarts=0` | 当时不是 Alloy 停机或反复重启 |
| 本机 `prometheus_remote_storage_samples_failed_total=0`，发送样本计数继续增长 | 没有支持 middleware 批量写入失败的证据 |
| `up{instance="middleware"}[15m]` 能返回多条样本，间隔约 60 秒且值为 1 | 采集和落库仍在进行 |
| 原始 `up` 最新样本距接收端查询时点约 366–386 秒 | 已超出 300 秒窗口；样本年龄包含时钟偏差及采集间隔 |
| 扩大窗口后能查到 `node_memory_MemAvailable_bytes` | 主机指标没有整体停止入库 |
| 两台 `NTPSynchronized=no`，时间同步日志多次超时 | 需要修复时钟同步，而不只是确认服务进程存活 |
| 从两台探测阿里云、腾讯 NTP 均成功，两个时间源返回一致 | 有可用的替代时间源；当轮测得 middleware 约慢 118 秒、docker-host 约快 220 秒 |
| Loki 精确查询 `{host="middleware"}` 能返回日志 | 宽泛查询被其他机器日志占满，不能用来判定该机无日志 |

Hermes 最初根据 **agent** 的 `400 out of order sample`，推断 middleware 也被整批拒收。接收端确实存在这类错误，但当时没有证明错误来自 middleware；后续本机发送计数和原始样本证据也不支持该归因。不能把其他主机的同型错误直接当成本机根因。

另外，时间戳相关查询有一个容易误用的地方：

```promql
# 可用于确认较大窗口内是否有数据。
last_over_time(up{job="node",instance="middleware"}[15m])

# 不要用它计算原始样本年龄：这里 timestamp 得到的是聚合结果时间。
time() - timestamp(last_over_time(up{job="node",instance="middleware"}[15m]))
```

后一个表达式可能返回 0，却不代表原始样本是刚采集的。应读取原始范围向量里的样本时间戳，再与查询时点比较。

## 排查 SOP

### 1. 核对时区、时钟和同步状态

在指标发送 VM 和 Prometheus 主机上分别执行：

```bash
date -Is
date +%s
timedatectl status
timedatectl timesync-status
journalctl -u systemd-timesyncd --since '24 hours ago' --no-pager -n 50
```

尽量在相近时刻对比两台的时间。`Asia/Shanghai` 只说明时区设置为 UTC+8，不代表系统时钟准确。NTP 服务为 active 也不代表同步成功，要看 `System clock synchronized`，以及实际时间源和最近同步记录。

如果两台时间不同，不能直接认定其中一台正确。本次两台相对标准时间都有偏差，应一起修复。

### 2. 区分“没采集”“没写入”和“时间戳太旧”

先查当前数据与告警：

```promql
up{instance="middleware"}
ALERTS{alertname="RemoteWriteStale",instance="middleware"}
```

再查原始范围数据。下式可通过 Prometheus instant-query API 查询；返回值中的 `values` 保留每条原始样本的时间戳：

```bash
curl -fsS --get http://192.168.31.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="node",instance="middleware"}[15m]'
```

如范围数据持续更新且 `up=1`，但即时查询为空，优先比较原始样本时间戳与 Prometheus 主机时钟。也可扩大窗口核对主机指标：

```promql
last_over_time(node_memory_MemAvailable_bytes{instance="middleware"}[15m])
```

必要时在发送 VM 查看 Alloy 状态及本机远程写入计数：

```bash
systemctl status alloy --no-pager
journalctl -u alloy --since '30 minutes ago' --no-pager -n 50
curl -fsS http://127.0.0.1:12345/metrics |
  rg '^prometheus_remote_storage_(samples_failed_total|samples_total|samples_pending|queue_highest_sent_timestamp_seconds)'
```

累计失败数要结合进程启动时间和前后变化判断；发送计数增长与接收端原始样本更新一起核对，才能确认链路。

### 3. 直接修改已有时间同步配置

本次选择维护已有 `/etc/systemd/timesyncd.conf`，不另外创建 `/etc/systemd/timesyncd.conf.d/` 文件。

```bash
sudoedit /etc/systemd/timesyncd.conf
```

在已有 `[Time]` 段内取消注释或修改 `NTP=`，其余无关配置保留：

```ini
[Time]
NTP=ntp.aliyun.com ntp.tencent.com
```

随后启用同步并重启服务：

```bash
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
```

如果主配置修改后未生效，可读取有效配置，检查是否已有 drop-in 或其他时间源覆盖；先确认内容和来源，再决定如何处理：

```bash
systemd-analyze cat-config systemd/timesyncd.conf
timedatectl timesync-status
```

NTP 使用 UDP 123。普通 HTTP 代理环境变量不会自动代理 NTP；域名走代理是否有效取决于 TUN／透明代理是否接管并支持 UDP。本次没有验证代理是故障原因，已验证国内时间源直连可用。

### 4. 验证同步和监控恢复

等待同步后，在各 VM 检查：

```bash
timedatectl status
timedatectl timesync-status
date -Is
```

确认 `System clock synchronized: yes`，时间源正确，机器间时间基本一致。随后在 Prometheus 查看：

```promql
up{job="node",instance="middleware"}
up{job="alloy",instance="middleware"}
node_memory_MemAvailable_bytes{instance="middleware"}
ALERTS{alertname="RemoteWriteStale",instance="middleware",alertstate="firing"}
```

本次 Alloy 采集周期约 60 秒，规则评估周期 30 秒。应观察多个采集周期，确认 `up` 持续为 1、主机指标时间戳跟随当前时间、告警不再 firing。校时不会自动补齐历史空洞；如果接收端时钟向后校正，还可能短暂受到已有未来时间戳影响，需要继续观察至时间追平。

## 这次留下的经验

- 看到 remote write“断流”，先核对发送端与接收端时钟，再考虑重启采集器或放宽接收策略。
- “时区一致”“NTP 服务运行”“系统时钟已同步”是三个不同状态，验收必须落到最后一个。
- 按故障主机精确查询日志和指标，其他主机的错误只能作为排查线索。
- 本次没有依据通过放宽 `out_of_order_time_window` 或降低告警灵敏度来解决问题；先修复时间同步。
- 保持配置入口简单：已有主配置能够完成的修改，直接维护原文件。
