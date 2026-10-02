---
publish: true
tags:
  - Loki
  - 最佳实践
cssclasses:
  - Loki
---

来源：https://grafana.com/docs/loki/latest/configure/bp-configure/

相关：[[Loki 标签最佳实践]]、[[Loki 快速上手教程]]

## 1. 日志时间顺序（Time ordering）

### 规则

> 对**同一个日志流**，日志必须按时间递增发送。如果收到的日志时间戳比该流最近一条更早，这条日志会被丢弃。

- 限制**只针对单个流**，不是全局。流由标签组合决定（见 [[Loki 标签最佳实践]]）。

### 问题示例：同一个流里乱序

```
{job="syslog"} 00:00:00 i'm a syslog!
{job="syslog"} 00:00:02 i'm a syslog!
{job="syslog"} 00:00:01 i'm a syslog!   <- 乱序，被拒绝
```

### 修复示例：加一个能区分来源的标签，拆成不同的流

```
{job="syslog", instance="host1"} 00:00:00 i'm a syslog!
{job="syslog", instance="host1"} 00:00:02 i'm a syslog!
{job="syslog", instance="host2"} 00:00:01 i'm a syslog!   <- 新流，接受
{job="syslog", instance="host1"} 00:00:03 i'm a syslog!   <- 在 host1 流内递增，接受
{job="syslog", instance="host2"} 00:00:02 i'm a syslog!   <- 在 host2 流内递增，接受
```

多台机器往同一个流写日志是乱序的最常见原因，所以标签里要有能唯一标识来源的静态标签（如 `instance`、`host`、`pod`）。

### 应用自身产生乱序

- 不要用 Alloy 的 `stage.timestamp` 从日志内容里解析时间戳，让采集端在读取时自动分配时间戳。
- 或者直接修复应用。

### 误报

批量写入时部分成功、或重放（replay）都可能出现「乱序」错误，不一定是真的乱序。

### 页面里的矛盾点

页面同时写了「必须递增，否则丢弃」和「Loki 默认接受乱序写入」。配置推荐里也有 `unordered_writes: true`。**两句话不能都按字面理解**，我判断是页面保留了旧版规则的描述，新版本默认允许一定窗口内的乱序，但页面没说明窗口大小，以你使用的 Loki 版本的行为为准，并实测。

## 2. 认证

Loki 自身**没有内置认证**。必须在前面放一个带认证的反向代理（如 nginx），否则谁都能访问。（[[Loki 快速上手教程]] 里的 `auth_enabled: false` 只适合本地。）

## 3. 缓存

页面说明要做多级缓存，详细指引「后续补充」，目前没有内容。

## 4. 压缩算法

| 算法 | 特点 | 适用 |
|---|---|---|
| gzip（默认，已用 `/config` 实测确认） | 压缩率高，但慢，负载高时查询响应会变慢 | 存储优先 |
| snappy（推荐） | 速度快，压缩率不如 gzip | 高吞吐 |
| LZ4 | 速度略慢于 snappy，但压缩率更高，对象存储里的 chunk 更小 | 折中 |

```yaml
ingester:
  chunk_encoding: snappy
```

## 5. 用 chunk_target_size 让 chunk 尽量填满

- 目标：每个 chunk 压缩后约 **1.5MB**，chunk 越大处理越高效。
- 填满 1.5MB 需要约 5–10 倍的原始日志（页面写作 7.5–10MB，压缩率取决于 snappy 或 gzip）。
- 相关参数：

| 参数 | 默认 | 作用 |
|---|---|---|
| `max_chunk_age` | 2h | chunk 在内存里的最长时间；限制内存占用和崩溃恢复窗口 |
| `chunk_idle_period` | 30m | 流多久没新日志就刷盘；限制内存占用和日志暴露时间 |

- chunk 是**按流**存在的，流越多，内存中的 chunk 越多，越容易在填满之前就因超时被刷盘。
- 小而未填满的 chunk 会拖慢 Loki。
- 高日志量的应用，如果能在远小于 `max_chunk_age` 的时间里填满 chunk，用动态标签才是合理的。

## 6. 调试参数

| 参数 | 作用 |
|---|---|
| `-print-config-stderr` | 启动时把完整配置打印到 stderr，命令行启动时方便快速核对 |
| `-log-config-reverse-order` | 反转配置输出顺序，Grafana 的所有环境都在用，方便在 Explore 里从上往下读 |

不重启也能看生效配置：Loki 运行时可以直接请求 `/config` 接口（已在 Loki 3.x 容器里实测可用），返回合并默认值后的完整 YAML：

```bash
curl -s localhost:3100/config | sed -n '/^ingester:/,/^[a-z_]*:/p'     # 只看某一个顶层块
curl -s localhost:3100/config | grep -E "chunk_encoding|volume_enabled"   # 只看某几项
```

输出很长（包含大量未启用功能的默认值，如 consul、etcd、kafka），建议总是配合 `sed` / `grep` 只取需要的部分。

## 7. 推荐的生产 limits 配置

```yaml
limits_config:
  # 速率限制
  ingestion_rate_strategy: global
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  per_stream_rate_limit: 3MB
  per_stream_rate_limit_burst: 15MB

  # 流数量限制
  max_global_streams_per_user: 10000
  max_streams_per_user: 0

  # 校验
  max_line_size: 256KB
  max_line_size_truncate: false
  max_label_name_length: 1024
  max_label_value_length: 2048
  max_label_names_per_series: 15

  # 时间约束
  reject_old_samples: true
  reject_old_samples_max_age: 168h   # 7 天
  creation_grace_period: 10m
  unordered_writes: true
```

## 8. 推荐的 ingester 配置

```yaml
ingester:
  chunk_idle_period: 30m
  chunk_target_size: 1572864    # 1.5 MB
  chunk_encoding: snappy
  max_chunk_age: 2h

  wal:
    enabled: true
    dir: /loki/wal
    checkpoint_duration: 5m
    flush_on_shutdown: true
```

WAL（预写日志）保证 ingester 崩溃后能恢复内存里还没刷盘的数据，`flush_on_shutdown` 让正常关闭时把数据刷出去。

## 9. 实测：一份 homelab 单机配置的生效值

下面是我在自己的 Docker 单机 Loki 上用 `/config` 实测的结果。配置文件里没有写 `ingester` 块，全部走默认值。

| 项 | 生效值 | 与本页推荐值对比 |
|---|---|---|
| `chunk_encoding` | `gzip` | 默认值；推荐 snappy，但低吞吐的 homelab 保持 gzip 更省磁盘 |
| `chunk_target_size` | `1572864`（1.5MB） | 默认值，已与推荐一致，无需手写 |
| `max_chunk_age` | `2h` | 一致 |
| `chunk_idle_period` | `30m` | 一致 |
| `wal.enabled` | `true` | 默认已开启 |
| `wal.dir` | `/loki/wal` | 跟随 `common.path_prefix` |
| `wal.flush_on_shutdown` | `false` | 与推荐的 `true` 不同；WAL 持久化时重启会重放，不丢数据 |
| `limits_config.volume_enabled` | `true` | 默认开启，无需手写 |
| `limits_config.allow_structured_metadata` | `true` | 默认开启，无需手写 |

结论：**本页第 8 节的推荐值，大部分是默认值，单机自建时不用逐项写进配置**。真正要自己写的只有：存储路径、`schema_config`、`retention_period` 和 `compactor.retention_enabled`。

部署时必须确认的一点：`/loki`（chunks、WAL、compactor 都在这里）要挂持久化卷，否则容器重建后数据全部丢失：

```bash
docker inspect <loki容器名> --format '{{json .Mounts}}'    # 应看到 Destination 为 /loki 的 volume 或 bind
```

`docker compose down -v` 会删除命名卷，日常操作不要带 `-v`。
