---
publish: true
tags:
  - 部署
---

对应官方 Send logs to Loki 教程，四个组件串成一条日志采集链路：`local.file_match`（找文件）→ `loki.source.file`（读文件内容）→ `loki.process`（过滤/处理）→ `loki.write`（写入 Loki）。概念背景见 [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] 里的"日志管道"模式。

## 前提

- Loki 实例（本教程用 Docker Compose 起一个）
- Grafana 用来查日志（Explore 页面，配 Loki 数据源）
- Alloy 已安装并跑起来（`http://localhost:12345` 能打开 UI）

## 本地 Loki + Grafana 环境（用于验证）

```yaml
version: '3'
services:
  loki:
    image: grafana/loki:3.0.0
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml

  prometheus:
    image: prom/prometheus:v2.47.0
    command:
      - --web.enable-remote-write-receiver
      - --config.file=/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    environment:
      - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    entrypoint:
      - sh
      - -euc
      - |
        mkdir -p /etc/grafana/provisioning/datasources
        cat <<EOF > /etc/grafana/provisioning/datasources/ds.yaml
        apiVersion: 1
        datasources:
        - name: Loki
          type: loki
          access: proxy
          orgId: 1
          url: http://loki:3100
          basicAuth: false
          isDefault: false
          version: 1
          editable: false
        - name: Prometheus
          type: prometheus
          orgId: 1
          url: http://prometheus:9090
          basicAuth: false
          isDefault: true
          version: 1
          editable: false
        EOF
        /run.sh
    image: grafana/grafana:11.0.0
    ports:
      - "3000:3000"
```

`docker compose up -d` 起完，Grafana 访问 `http://localhost:3000`，数据源已经通过 provisioning 自动配好，不用手动加。

## Alloy 配置：`config.alloy`

### 1. 找文件：`local.file_match`

```alloy
local.file_match "local_files" {
  path_targets = [{"__path__" = "/var/log/*.log"}]
  sync_period  = "5s"
}
```

按 glob 模式匹配日志文件路径，每 5 秒重新扫描一次目录，捕捉新出现的日志文件（比如按天轮转产生的新文件）。

### 2. 读文件：`loki.source.file`

```alloy
loki.source.file "log_scrape" {
  targets       = local.file_match.local_files.targets
  forward_to    = [loki.process.filter_logs.receiver]
  tail_from_end = true
}
```

接上一步匹配到的文件列表，持续 tail 读取新增内容。`tail_from_end = true` 表示只读启动之后新写入的行，不会把历史全量日志一次性倒进去——这个参数很关键，第一次上线一个已经写了很久的日志文件时如果漏设，会把历史日志全部灌进 Loki。

### 3. 过滤：`loki.process`

```alloy
loki.process "filter_logs" {
  stage.drop {
    source              = ""
    expression          = ".*Connection closed by authenticating user root"
    drop_counter_reason = "noisy"
  }
  forward_to = [loki.write.grafana_loki.receiver]
}
```

`stage.drop` 用正则匹配到就整行丢弃，这里过滤掉 SSH 爆破扫描产生的噪音日志（`root` 认证被拒的连接记录），`drop_counter_reason` 是给丢弃计数打的标签，方便在 Alloy 自身的 metrics 里统计"因为什么原因丢了多少行"。更复杂的处理（提取字段、加标签）参考 [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] 里 `stage.logfmt`/`stage.labels`/`stage.json`/`stage.match` 那几个例子，`loki.process` 内部可以叠多个 `stage.*` 顺序执行。

### 4. 写入：`loki.write`

```alloy
loki.write "grafana_loki" {
  endpoint {
    url = "http://localhost:3100/loki/api/v1/push"

    // basic_auth {
    //  username = "admin"
    //  password = "admin"
    // }
  }
}
```

Loki 开了鉴权的话把 `basic_auth` 取消注释填上账号密码。

## 加载配置

```bash
# macOS
sudo cp config.alloy $(brew --prefix)/etc/alloy/config.alloy

# Linux
sudo cp config.alloy /etc/alloy/config.alloy
```

热重载（不重启进程），对应 [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] 里讲的两种触发方式：

```bash
curl -X POST http://localhost:12345/-/reload
```

或者直接重启服务：

```bash
# macOS
brew services restart grafana/grafana/alloy

# Linux
sudo systemctl reload alloy
```

## 验证

1. Alloy UI（`http://localhost:12345`）的 **Graph** 标签能看到四个组件连成的管道图，颜色代表健康状态（对应 [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] 的四种健康状态）
2. Grafana Explore（`http://localhost:3000/explore`）选 Loki 数据源，点 **Label Browser** 选日志文件对应的标签，能查到日志内容即为端到端打通

## 实际部署：Docker Host（homelab 在用的版本）

教程版本只采文件日志，homelab 实际的 `config.alloy` 多了 Docker 容器日志这条线，两条管道并行：

```alloy
log_level = "debug"

// ============================
// Docker 容器日志采集
// ============================

// 发现本机所有 Docker 容器
discovery.docker "local" {
  host = "unix:///var/run/docker.sock"
}

// 从容器名中提取标签
discovery.relabel "docker_labels" {
  targets = []

  rule {
    source_labels = ["__meta_docker_container_name"]
    regex         = "/(.*)"
    target_label  = "container_name"
  }

  rule {
    target_label = "instance"
    replacement  = constants.hostname
  }
}

// 采集容器 stdout/stderr 日志
loki.source.docker "containers" {
  host          = "unix:///var/run/docker.sock"
  targets       = discovery.docker.local.targets
  relabel_rules = discovery.relabel.docker_labels.rules
  forward_to    = [loki.process.docker_logs.receiver]
}

// 处理 Docker 日志：给所有容器日志打 job 标签
loki.process "docker_logs" {
  forward_to = [loki.write.local.receiver]

  stage.static_labels {
    values = {
      job = "docker",
    }
  }
}

// ============================
// 系统日志采集
// ============================

// 匹配系统日志文件
local.file_match "syslog" {
  path_targets = [
    {"__path__" = "/var/log/syslog",   "job" = "syslog",  "host" = "docker-host"},
    {"__path__" = "/var/log/auth.log", "job" = "authlog", "host" = "docker-host"},
  ]
  sync_period = "5s"
}

// 采集系统日志文件
loki.source.file "syslog" {
  targets       = local.file_match.syslog.targets
  forward_to    = [loki.write.local.receiver]
  tail_from_end = true
}

// ============================
// 写入 Loki
// ============================

loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

### 和教程版本的关键差异

**Docker 容器日志用专门的组件**，不是读文件：`discovery.docker` 发现本机所有容器 → `discovery.relabel` 定义打标签规则（只导出 `.rules`，不需要 `.output`，所以 `targets = []` 留空没问题）→ `loki.source.docker` 直接读容器 stdout/stderr（走 Docker socket，不是读磁盘上的日志文件）→ `loki.process` 统一打 `job = "docker"` 标签。这条链路能让 Grafana 里按 `container_name` 区分不同容器的日志，比把所有容器日志混在一起强得多。

`discovery.relabel` 里两条规则：第一条从 `__meta_docker_container_name`（Docker 原生带的 `/容器名` 格式）用正则 `/(.*)`  提取出不带斜杠的容器名，写进 `container_name` 标签（`replacement` 没写，用的是默认值 `"$1"`，对应正则的捕获组）；第二条给所有日志加一个 `instance` 标签，值是 `constants.hostname`。

> **⚠️ 坑**：`constants.hostname` 取的是 **Alloy 进程自己看到的 hostname**。Alloy 是用 Docker 部署的，容器有独立的 hostname 命名空间，默认就是**容器 ID**，不是宿主机的真实 hostname——这条规则实际上没有达到"标出是哪台物理机"的目的，反而打上一串没意义的容器 ID。
>
> **最简单的修法：直接硬编码。**
>
> ```alloy
> rule {
>   target_label = "instance"
>   replacement  = "docker-host"   // 手写死机器名
> }
> ```
>
> 部署模式本来就是"哪台机子采日志就去哪台机子上单独装一份 Alloy、改一份配置"（见 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]]），不存在"一份配置到处复制"的场景，硬编码没有多机器场景下改漏的风险，比传环境变量更省事。真要多机器共用同一份配置模板时，再上环境变量方案：
>
> ```yaml
> # docker-compose.yml
> services:
>   alloy:
>     environment:
>       - HOST_HOSTNAME=${HOSTNAME}
> ```
>
> ```alloy
> rule {
>   target_label = "instance"
>   replacement  = sys.env("HOST_HOSTNAME")
> }
> ```

**系统日志走静态文件 + 静态标签**，`path_targets` 里直接把 `job`/`host` 标签写死在 target 对象里（普通字段自动变标签，参考 [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] 里讲过的同一套机制），所以不需要单独过一遍 `loki.process`，比教程版本少一步。

**`loki.write` 的 URL 用的是 `http://loki:3100`**，不是 `localhost`——因为 Alloy 和 Loki 大概率在同一个 Docker Compose 网络里，`loki` 是容器名，靠 Docker 内置 DNS 解析，这也是为什么 Alloy 本身多半也是用 Docker 部署的（对应 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里"容器化服务用容器部署更省事"的判断）。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — 日志管道的通用模式和更复杂的 stage 组合
- [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] — 热重载、健康状态
- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 什么场景下值得部署 Alloy
- [[监控告警链路追踪/日志/Alloy 处理日志（多阶段 Pipeline）.md]] — loki.process 内部多个 stage 怎么串联
