---
publish: true
tags:
  - Alloy
  - Ansible
  - 部署
  - homelab
cssclasses:
  - Alloy
---
> 日期：2026-10-07
> 背景：bastion 只有 node_exporter（没有日志采集），middleware 什么都没装——Prometheus 一直抓它的 9100 端口，其实 node_exporter 从没装过。统一换成 Alloy：一个进程同时负责指标和日志，和 agent / database 的做法一致。
> 执行环境：agent VM 上的 Ansible（`/etc/ansible`、`/root/ansible-playbooks/`），用 [[Alloy 安装 - Ansible]] 里的官方 `grafana.grafana.alloy` role。

---

## 最终结果

| 机器 | 之前 | 之后 |
|---|---|---|
| bastion（192.168.31.3） | node_exporter，Prometheus 抓 9100；无日志 | Alloy：指标 remote write + syslog / auth / kern + **frpc journal**；node_exporter 已删除 |
| middleware（192.168.31.6） | 什么都没有（抓取目标一直 down） | Alloy：指标 remote write + syslog / auth / kern + **docker 容器日志**（redis） |

Playbook 中配置的预期标签如下；指标标签与日志标签的意图是跟 agent 保持一致：

- 指标：`job="node"`、`instance=<主机名>`；Alloy 自身指标 `job="alloy"`
- 日志：`host=<主机名>`、`cluster="homelab"`、`job=syslog|authlog|kernlog|frpc|docker`

2026-10-15 从 Loki 核对到一处运行时偏差：bastion 的 Alloy 配置文件为 frpc journal 源设置 `job="frpc"`，但 Loki 实际 stream 标签是 `job="loki.source.journal.frpc"`。`FrpcReconnecting` 规则当前按 `{job="frpc"}` 查询，所以没有匹配到这批日志；该规则已加载不等于已验证可命中。偏差原因尚未确认，修复记录见 [[Loki 日志告警与监控组件自监控]]。

---

## Playbook：`/root/ansible-playbooks/deploy-alloy-node-logs.yml`

一份配置模板，按主机名追加各自的日志源：

```yaml
- name: Deploy Alloy (metrics + logs)
  hosts: bastion,middleware
  become: true

  vars:
    prometheus_write_url: "http://192.168.31.1:9090/api/v1/write"
    loki_push_url: "http://192.168.31.1:3100/loki/api/v1/push"

    alloy_version: "1.19.2"
    alloy_download_url_deb: "https://apt.grafana.com/pool/main/a/alloy/alloy-{{ alloy_version }}-1.{{ __alloy_arch }}.deb"

    # 每台机器的额外日志源
    alloy_extra_logs:
      bastion: |
        loki.source.journal "frpc" {
          matches       = "_SYSTEMD_UNIT=frpc.service"
          labels        = {"job" = "frpc", "host" = "bastion"}
          forward_to    = [loki.process.add_labels.receiver]
          max_age       = "1h"
        }
      middleware: |
        discovery.docker "containers" {
          host = "unix:///var/run/docker.sock"
        }
        discovery.relabel "containers" {
          targets = []
          rule {
            source_labels = ["__meta_docker_container_name"]
            regex         = "/(.*)"
            target_label  = "container_name"
          }
        }
        loki.source.docker "containers" {
          host          = "unix:///var/run/docker.sock"
          targets       = discovery.docker.containers.targets
          relabel_rules = discovery.relabel.containers.rules
          labels        = {"job" = "docker", "host" = "middleware"}
          forward_to    = [loki.process.add_labels.receiver]
        }

    alloy_user_groups: "{{ ['adm', 'systemd-journal'] + (['docker'] if inventory_hostname == 'middleware' else []) }}"

    alloy_config: |
      logging {
        level = "warn"
      }

      prometheus.exporter.unix "default" {
        include_exporter_metrics = true
        disable_collectors       = ["mdadm"]
      }

      discovery.relabel "unix_job" {
        targets = prometheus.exporter.unix.default.targets
        rule {
          target_label = "job"
          replacement  = "node"
        }
        rule {
          target_label = "instance"
          replacement  = "{{ inventory_hostname }}"
        }
      }

      prometheus.scrape "default" {
        targets = array.concat(
          discovery.relabel.unix_job.output,
          [{
            job         = "alloy",
            instance    = "{{ inventory_hostname }}",
            __address__ = "127.0.0.1:12345",
          }],
        )
        forward_to = [prometheus.remote_write.default.receiver]
      }

      prometheus.remote_write "default" {
        endpoint {
          url = "{{ prometheus_write_url }}"
        }
      }

      local.file_match "syslog" {
        path_targets = [
          {"__path__" = "/var/log/syslog",   "job" = "syslog",  "host" = "{{ inventory_hostname }}"},
          {"__path__" = "/var/log/auth.log", "job" = "authlog", "host" = "{{ inventory_hostname }}"},
          {"__path__" = "/var/log/kern.log", "job" = "kernlog", "host" = "{{ inventory_hostname }}"},
        ]
        sync_period = "5s"
      }

      loki.source.file "syslog" {
        targets       = local.file_match.syslog.targets
        forward_to    = [loki.process.add_labels.receiver]
        tail_from_end = true
      }

      {{ alloy_extra_logs[inventory_hostname] | default('') }}

      loki.process "add_labels" {
        forward_to = [loki.write.default.receiver]
        stage.static_labels {
          values = {
            cluster = "homelab",
          }
        }
      }

      loki.write "default" {
        endpoint {
          url = "{{ loki_push_url }}"
        }
      }

  tasks:
    - name: Install and configure Alloy
      ansible.builtin.include_role:
        name: grafana.grafana.alloy
```

> 用 `{{ inventory_hostname }}` 而不是 Alloy 的 `constants.hostname`：标签以 inventory 为准，不受机器 hostname 影响。
> Alloy 配置里的 `{ }` 和 Jinja 的 `{{ }}` 不冲突，可以直接写在 `alloy_config` 里。
> `alloy_user_groups`：读 `/var/log/*` 要 `adm`，读 journal 要 `systemd-journal`，读容器日志要 `docker`。role 加完组后会重启 Alloy，组权限才生效。

---

## 执行

```bash
ssh agent
export PATH=$HOME/.local/bin:$PATH       # ansible 是 pipx 装的，非交互 ssh 时 PATH 里没有
cd /root/ansible-playbooks

ansible-playbook deploy-alloy-node-logs.yml --syntax-check
ansible-playbook deploy-alloy-node-logs.yml --limit middleware --check --diff    # 先试跑看 diff
ansible-playbook deploy-alloy-node-logs.yml --limit middleware
```

### bastion 的切换顺序

bastion 原来由 Prometheus 抓 9100，切到 remote write 后两路数据的标签完全相同（`job="node", instance="bastion"`），同时存在会互相冲突。顺序：

1. `prometheus.yml` 里注释掉 bastion 的 9100 抓取目标 → `docker kill -s HUP prometheus`
2. 部署 Alloy：`ansible-playbook deploy-alloy-node-logs.yml --limit bastion`
3. 确认 Alloy 正常后停掉 node_exporter：`ansible bastion -m shell -a "systemctl disable --now node_exporter"`
4. 稳定后彻底删除（按 [[阿里云 ECS 监控部署文档]] 的安装步骤，只有这两个文件；没有专用用户，也没有防火墙规则）：

```bash
rm -f /usr/local/bin/node_exporter /etc/systemd/system/node_exporter.service
systemctl daemon-reload
```

中间只有一两分钟的指标空档。

### docker-host 上同步改告警规则

remote write 的机器挂了只会停止推送，`up` 不会变成 0，要在两条规则里加上新机器：

```yaml
# rules/node-up.yml → RemoteWriteStale
          or
          absent_over_time(up{job="node", instance="bastion"}[5m])
          or
          absent_over_time(up{job="node", instance="middleware"}[5m])
```

```yaml
# loki-rules/log-alerts.yml → LogIngestionStopped
          or
          label_replace(absent_over_time({host="bastion"}[15m]), "instance", "bastion", "", "")
          or
          label_replace(absent_over_time({host="middleware"}[15m]), "instance", "middleware", "", "")
```

---

## 验证

```bash
# 指标：5 台都应为 1
curl -s localhost:9090/api/v1/query --data-urlencode 'query=up{job="node"}' | jq -r '.data.result[]|"\(.metric.instance)=\(.value[1])"'

# 日志：按 host/job 统计最近 10 分钟
curl -s -G localhost:3100/loki/api/v1/query \
  --data-urlencode 'query=sum by (host,job) (count_over_time({host=~"bastion|middleware"}[10m]))'

# 目标机上看 Alloy 各组件是否健康
curl -s 127.0.0.1:12345/api/v0/web/components | python3 -c 'import sys,json; [print(c["localID"], c["health"]["state"]) for c in json.load(sys.stdin)]'
```

---

## 踩坑

| 现象 | 原因 | 处理 |
|---|---|---|
| role 安装卡住 / 很慢 | 默认从 GitHub release 下载 160MB 的 deb，国内 20s 都下不完 | `alloy_download_url_deb` 改成 `https://apt.grafana.com/pool/main/a/alloy/alloy-<版本>-1.<arch>.deb`（约 4MB/s） |
| 部署后 Alloy 报一次 `status=400` 丢弃数据 | `loki.source.docker` 首次会读容器全部历史日志，redis 最后一条日志是一个月前的，Loki 拒收过旧条目 | 只发生一次，新日志正常；不用处理 |
| Loki 里看不到 frpc 日志 | 部署时 frpc 近期没输出；`max_age = "1h"` 不回填更早的 journal | 等 frpc 有新输出；需要历史就临时调大 `max_age` |
| `ansible: command not found` | pipx 安装在 `~/.local/bin`，非交互 ssh 不加载 profile | `export PATH=$HOME/.local/bin:$PATH` |
| `systemctl is-active node_exporter` 让 ad-hoc 报 FAILED | 服务已停，`is-active` 返回 3 | 预期行为，看输出是 `inactive` 就对了 |

---

## 用 frpc 日志定位到的问题

frpc 日志一接进来，就解释了 2026-10-07 凌晨两次 NtfyPublicDown（ntfy 公网入口不可用）：

```
01:47:28 [W] connect to server error: session shutdown
01:50:06 [W] connect to server error: connection write timeout
01:52:01 [W] connect to server error: connection write timeout
01:52:05 [I] login to server success
```

frpc 和 ECS 上的 frps 之间反复断线，问题出在 bastion → ECS 这段隧道。为此新增日志告警 **FrpcReconnecting**（10 分钟内连接失败 > 3 次），见 [[Loki 日志告警与监控组件自监控]]。

---

## 后续新机器怎么接

1. agent 的 `/etc/ansible/hosts` 里加主机
2. playbook 的 `hosts:` 加上它；有特殊日志源就在 `alloy_extra_logs` 里加一段
3. `--check --diff` → 正式执行
4. docker-host 上 RemoteWriteStale、LogIngestionStopped 两条规则各加一行

## 相关笔记

- [[Alloy 安装 - Ansible]] — 官方 role 的基本用法
- [[Alloy 采集 Loki 日志实战记录]] — agent 上的同类配置（手工部署）
- [[Alloy 接入 Prometheus 实战记录]] — remote write 链路
- [[Loki 日志告警与监控组件自监控]] — 日志告警规则
