---
publish: true
tags:
  - 部署
---
# mysql部署prometheus

# MySQL Exporter 部署文档

## 概述

在云服务器上部署 mysqld_exporter，采集 MySQL 指标到 Prometheus，通过 Grafana 可视化监控。

## 架构

```
MySQL (云服务器)
    ↓
mysqld_exporter (云服务器:9104)
    ↓
Prometheus (本地采集)
    ↓
Grafana (展示面板)
```


---

## 第一步：云服务器部署 mysqld_exporter

### 1.1 下载和解压

```bash
cd /root
wget https://github.com/prometheus/mysqld_exporter/releases/download/v0.19.0/mysqld_exporter-0.19.0.linux-amd64.tar.gz
tar xzf mysqld_exporter-0.19.0.linux-amd64.tar.gz
```

### 1.2 创建 MySQL 配置文件

```bash
cat > /root/.my.cnf << 'EOF'
[client]
password=MySQL密码
EOF

chmod 600 /root/.my.cnf
```

### 1.3 复制到系统路径

```bash
sudo cp /root/mysqld_exporter-0.19.0.linux-amd64/mysqld_exporter /usr/local/bin/
```

### 1.4 注册为 systemd 服务

```bash
sudo tee /etc/systemd/system/mysqld_exporter.service > /dev/null << 'EOF'
[Unit]
Description=Mysqld Exporter
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/mysqld_exporter \
  --web.listen-address=":9104" \
  --mysqld.username="pve" \
  --mysqld.address="localhost:3306" \
  --config.my-cnf="/root/.my.cnf" \
  --collect.global_status \
  --collect.global_variables \
  --collect.slave_status \
  --collect.info_schema.innodb_cmp \
  --collect.info_schema.innodb_cmpmem \
  --collect.info_schema.query_response_time \
  --collect.engine_innodb_status \
  --collect.engine_tokudb_status \
  --collect.perf_schema.tableiowaits \
  --collect.perf_schema.indexiowaits \
  --collect.perf_schema.tablelocks \
  --collect.perf_schema.eventsstatements \
  --collect.perf_schema.eventsstatementssum \
  --collect.perf_schema.eventswaits \
  --collect.perf_schema.file_events \
  --collect.perf_schema.file_instances \
  --collect.perf_schema.memory_events \
  --collect.info_schema.processlist \
  --collect.info_schema.tables \
  --collect.info_schema.innodb_tablespaces \
  --collect.info_schema.innodb_metrics \
  --collect.mysql.user \
  --collect.auto_increment.columns \
  --collect.binlog_size
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

### 1.5 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl start mysqld_exporter
sudo systemctl enable mysqld_exporter

# 验证状态
sudo systemctl status mysqld_exporter
```

### 1.6 验证 exporter 是否正常运行

```bash
curl http://localhost:9104/metrics | head -20
```


---

## 第二步：Prometheus 配置

在本地 Prometheus 配置文件 `/opt/monitoring/prometheus/prometheus.yml` 中添加 MySQL 采集任务：

```yaml
- job_name: 'mysql'
  static_configs:
    - targets: ['云服务器IP:9104']
```

**示例：**

```yaml
- job_name: 'mysql'
  static_configs:
    - targets: ['192.168.31.100:9104']
```

### 重启 Prometheus

```bash
sudo systemctl restart prometheus
```

### 验证数据采集


1. 打开 Prometheus Web UI：`http://localhost:9090`
2. 进入 **Status** → **Targets**
3. 查看 `mysql` job 是否显示为 **UP** 状态


---

## 第三步：Grafana 导入面板

### 3.1 推荐的 MySQL 面板

| 面板名称 | ID | 特点 |
|----|----|----|
| MySQL Dashboard | 14031 | 综合监控，包含内存、网络、CPU |
| MySQL Exporter Quickstart | 14057 | 快速启动，包含告警规则 |
| MySQL Overview | 7362 | Percona 项目，全面的指标 |
| Mysqld Exporter Dashboard CN | 17320 | 中文界面 |

### 3.2 导入步骤


1. 打开 Grafana：`http://localhost:3000`
2. 左侧菜单 → **仪表板** → **新建** → **导入仪表板**
3. 输入面板 ID（如 `14031`）
4. 点击 **Load**
5. 选择 Prometheus 数据源
6. 点击 **Import**

### 3.3 推荐导入的面板

* 先导入 ID `14031`（MySQL Dashboard）作为主面板
* 再导入 ID `14057`（Mysql Exporter Quickstart）作为补充


---

## 第四步：验证配置

### 4.1 检查 Prometheus 数据


1. 登录 Prometheus：`http://localhost:9090`
2. 在搜索框输入 `mysql_` 查看是否有数据
3. 示例查询：`mysql_global_status_questions`

### 4.2 查看 Grafana 面板


1. 登录 Grafana：`http://localhost:3000`
2. 打开已导入的 MySQL 仪表板
3. 验证图表是否显示数据


---

## 常见问题

### Q: MySQL exporter 服务一直重启

**A:** 检查 `.my.cnf` 配置文件是否正确：

```bash
cat /root/.my.cnf
# 应该包含: [client] 和 password=xxx
```

### Q: Prometheus 中 MySQL targets 显示为 DOWN

**A:** 检查网络连通性：

```bash
# 在本地 Prometheus 所在服务器测试
curl http://云服务器IP:9104/metrics
```

### Q: Grafana 面板显示为 No data

**A:**


1. 确认 Prometheus 已采集数据（见第4.1步）
2. 检查面板选择的数据源是否正确
3. 重新选择 Prometheus 数据源后保存

### Q: 如何修改 exporter 监听的端口

**A:** 编辑 `/etc/systemd/system/mysqld_exporter.service`，修改 `--web.listen-address`:

```bash
sudo systemctl edit mysqld_exporter
# 修改后重启
sudo systemctl restart mysqld_exporter
```


---

## 服务管理

```bash
# 启动服务
sudo systemctl start mysqld_exporter

# 停止服务
sudo systemctl stop mysqld_exporter

# 重启服务
sudo systemctl restart mysqld_exporter

# 查看状态
sudo systemctl status mysqld_exporter

# 查看日志
sudo journalctl -u mysqld_exporter -f
```


---

## 相关链接

* [mysqld_exporter GitHub](https://github.com/prometheus/mysqld_exporter)
* [Prometheus MySQL Exporter 文档](https://prometheus.io/docs/guides/node-exporter/)
* [Grafana MySQL 仪表板库](https://grafana.com/grafana/dashboards/)