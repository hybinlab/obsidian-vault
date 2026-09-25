---
publish: true
---

`loki.*` 命名空间下所有组件的索引，按"数据源 → 处理 → 输出"分类，前面几篇笔记已经具体用到的会标注链接，没细讲的先记一句话作用，用到再展开。

## 数据源类（`loki.source.*`）：从哪读日志

| 组件 | 读什么 |
| --- | --- |
| [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md\|loki.source.file]] | 本地文件（已用） |
| [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md\|loki.source.docker]] | Docker 容器 stdout/stderr（已用） |
| [[监控告警链路追踪/日志/Alloy 处理日志（多阶段 Pipeline）.md\|loki.source.api]] | 监听 HTTP 端口接收推送（已讲） |
| `loki.source.journal` | **systemd journal**（journalctl 那套） |
| `loki.source.syslog` | Syslog 协议（RFC3164/5424），当接收端监听 UDP/TCP |
| `loki.source.kubernetes` | K8s 集群里的 Pod 日志（通过 API Server，不需要节点级 agent） |
| `loki.source.podlogs` | K8s Pod 日志的另一种采集方式（CRD 驱动，Promtail 迁移场景常见） |
| `loki.source.kubernetes_events` | K8s 事件（Event 对象，不是 Pod 日志） |
| `loki.source.kafka` | 从 Kafka topic 消费日志 |
| `loki.source.gelf` | GELF 格式（Graylog 生态常用） |
| `loki.source.windowsevent` | Windows 事件日志 |
| `loki.source.awsfirehose` | AWS Kinesis Firehose 数据流 |
| `loki.source.azure_event_hubs` | Azure Event Hubs |
| `loki.source.cloudflare` | Cloudflare 日志（走 Cloudflare Logpush） |
| `loki.source.gcplog` | Google Cloud Logging |
| `loki.source.heroku` | Heroku 应用日志 |

**跟我实际场景相关的一个**：之前排查 syslog 那篇笔记里提过一个隐患——"`/var/log/syslog` 依赖 rsyslog，纯 systemd-journald 系统可能没这个文件"。如果 docker-host 真遇到这个问题，正确解法就是把 `local.file_match` + `loki.source.file` 那条链路换成 `loki.source.journal`，直接读 journal，不用依赖 rsyslog 转储成文件。

## 处理类：读到之后怎么加工

| 组件 | 作用 |
| --- | --- |
| [[监控告警链路追踪/日志/Alloy 处理日志（多阶段 Pipeline）.md\|loki.process]] | 多阶段 `stage.*` 处理链（已讲） |
| `loki.relabel` | 独立的 relabel 组件，专门对**日志流的标签**做增删改，跟组件配置里常见的 `discovery.relabel`（对**服务发现 target**relabel）是两个不同东西，不要混淆——`discovery.relabel` 在采集之前决定"抓不抓、怎么打标签"，`loki.relabel` 在日志流已经产生之后再调整标签 |
| `loki.enrich` | 给日志追加额外的元数据/上下文（比如从外部数据源查到的信息） |
| `loki.secretfilter` | **脱敏**：过滤/遮蔽日志内容里的敏感信息（密钥、token 之类意外打印进日志的情况），值得在往公网转发日志前加一道 |

## 输出/工具类

| 组件 | 作用 |
| --- | --- |
| [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md\|loki.write]] | 写入 Loki（已用） |
| `loki.echo` | 把日志原样打印出来，不写 Loki——纯调试用，验证 pipeline 前半段有没有正确产出数据时用它兜底，不用起一个真 Loki 实例 |
| `loki.rules.kubernetes` | 管理 Loki 的告警规则（LogQL 版的 Prometheus alerting rule），在 K8s 环境里从 CRD 同步规则到 Loki |

## 小结

23 个组件里，homelab 实际会用到的核心集合不大：`loki.source.file`/`loki.source.docker`（采）+ `loki.process`（洗）+ `loki.write`（发）三四个，云厂商专属的（`gcplog`/`azure_event_hubs`/`cloudflare`/`heroku`）和 K8s 专属的（`kubernetes`/`podlogs`/`kubernetes_events`）用不上可以先跳过。`loki.source.journal`（万一 syslog 文件不存在）和 `loki.secretfilter`（脱敏）是两个值得记住、以后可能用得上的备选项。

## 相关笔记

- [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]]
- [[监控告警链路追踪/日志/Alloy 处理日志（多阶段 Pipeline）.md]]
