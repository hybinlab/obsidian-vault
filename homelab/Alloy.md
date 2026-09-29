# Alloy 部署与配置 SOP

> **适用场景**：Grafana Alloy 作为 Prometheus / Loki 采集 Agent，部署在需要被监控的 VM 上；
> 所有 VM 统一打 `cluster=homelab` 标签到 Loki/Prom 端，便于聚合查询。
> **原则**：密码、API Key 等凭据一律不进入本文档，配置文件路径与注入方式记录到位即可。

---

## 1. 架构总览

```text
┌─────────────────────────────────────────────────────────────┐
│  VM A (例: docker-host)                                       │
│    alloy  ────► loki.source.file ───► remote_write ──► Loki     │
│             ────► (无 Prometheus)                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  VM B (例: agent / database)                                  │
│    alloy  ────► prometheus.exporter.unix     ──► remote_write ──► Prom │
│             ────► prometheus.exporter.mysql                       │
│             ────► prometheus.exporter.postgres                    │
│             ────► loki.source.file             ──► Loki              │
└─────────────────────────────────────────────────────────────┘
```

- **Prometheus 端点**：`http://192.168.31.1:9090/api/v1/write`（docker-host）
- **Loki 端点**：`http://192.168.31.1:3100/loki/api/v1/push`
- **Alloy UI**：每台机器 `:12345`（仅内网）
- **统一标签**：`cluster=homelab`（Prom 与 Loki 双侧均需打）

---

## 2. 安装

走 `apt` 官方仓库（apt.grafana.com），systemd unit 默认带，无需自建。

```bash
# 参考 Ansible 剧本: ansible-playbooks/init-alloy
```

版本校验：

```bash
alloy --version
```

---

## 3. 配置

### 3.1 配置文件路径

| 文件 | 用途 |
|---|---|
| `/etc/alloy/config.alloy` | Alloy 主配置 |
| `/etc/default/alloy` | systemd EnvironmentFile（**注入凭据**，权限 644 是妥协方案） |
| `/etc/alloy/config.yaml` | OTel 模式配置（本环境不用） |
| `/var/lib/alloy/data` | Alloy 运行时数据目录 |

### 3.2 凭据注入（关键模式）

- **绝不**在 `config.alloy` 写密码字面量
- 走 systemd EnvironmentFile：`/etc/default/alloy`
- 配置里通过 `sys.env("VARIABLE_NAME")` 引用

例：

```hcl
prometheus.exporter.mysql "default" {
  data_source_name = "exporter:" + sys.env("MYSQL_EXPORTER_PASSWORD") + "@(localhost:3306)/"
}
```

### 3.3 模板（database VM 当前实例）

- `prometheus.exporter.unix "default"` → job=node
- `prometheus.exporter.mysql "default"` → job=mysql
- `prometheus.exporter.postgres "default"` → job=postgres
- `prometheus.scrape "default"` → 汇总三块 + alloy 自监控（`127.0.0.1:12345`）
- `prometheus.remote_write "default"` → `192.168.31.1:9090/api/v1/write`

---

## 4. 多机标签设计（防容器名冲突）

按多机同时跑容器的场景，**只用 `container_name` 不够** —— 跨机会撞名。

规范：

- **每台 VM 的 alloy 配置**都加 `host = <vm-name>` 静态标签
- 容器发现走 `discovery.docker`，再加 `container_name`
- 最终二维定位：`{host, container_name}`

未实施清单（已知缺口）：103/104/106/107 未装 Alloy；按需安装。

---

## 5. 部署记录（按 VM）

### 101 agent ✅

- node + Loki（日志路径见 `homelab/alloy-日志路径.md` 待补）
- 标签风格：`instance=agent`（动态 hostname 风格）

### 100 docker-host ✅

- 仅 Loki（容器日志）
- 标签风格：`instance=docker-host`（**硬编码**风格，有意保留差异）

### 103 database ✅

- node + mysql + postgres（pg 已落地配置，密码待用户填）
- 标签风格：与 101 一致

### 未装：102 bastion / 104 middleware / 105 win10 / 106 arch / 107 ubuntu

按需扩展。

---

## 6. 已知问题与债

### 6.1 Alloy out-of-order write（backlog #1）

`loki.process` 用了 `stage.timestamp`，导致 Loki 拒绝老样本（默认 `max_sample_age=30m`）。
修法：**去掉 timestamp stage**，让 Loki 用 Alloy 接收时刻作 sample time。
详见 [[homelab/Alloy out-of-order 复盘]]（待补）。

### 6.2 /etc/default/alloy 权限（安全债）

文件权限 644，root 拥有，全员可读，与"密码不存明文配置"红线冲突。
当前妥协：**先跑通**。
长期方案：`chown root:alloy /etc/default/alloy && chmod 640 /etc/default/alloy`，
加 `User=alloy`（systemd unit 已是）。

### 6.3 MySQL exporter 1045（database VM）

`MYSQL_EXPORTER_PASSWORD` env 变量有值，但 alloy 报 `1045 Access denied for user 'exporter'@'localhost'`。
可能原因：MySQL `exporter@localhost` 用户真实密码与 env 不一致。
查证路径：装 mysql-client → `mysql -uroot -p -e "SELECT User, Host FROM mysql.user"`。

### 6.4 跨机 alloy 标签规范不一致（已记不修）

100 `instance=docker-host` 硬编码、101/103 `instance=agent/<hostname>` 动态。
原因：100 是早期硬编码定下，101/103 按风格学的；两者并存属"预占多机扩展"的有意差异化。

---

## 7. 验证清单（部署后必跑）

```bash
# 1. Alloy 进程健康
systemctl is-active alloy

# 2. UI 可达
curl -s http://127.0.0.1:12345/-/ready

# 3. Exporter 在监听
ss -ltnp | grep -E "9104|9187"

# 4. Prom 端能查到
curl -s 'http://192.168.31.1:9090/api/v1/query?query=up{job="postgres"}' | jq .

# 5. Loki 端能查到
curl -s 'http://192.168.31.1:3100/loki/api/v1/query?query={cluster="homelab"}' | jq .
```

---

## 8. 变更日志

- **2026-09-28**：database VM 新增 `prometheus.exporter.postgres` + `discovery.relabel.postgres_job`，
  接入 `prometheus.scrape.default.targets`；`POSTGRES_EXPORTER_PASSWORD` 待用户填入。
  备份：`config.alloy.bak.2026-09-28`、`/etc/default/alloy.bak.2026-09-28`。
  坑：原写法用 `data_source_name`（单数），正确是 `data_source_names`（复数 + array）。