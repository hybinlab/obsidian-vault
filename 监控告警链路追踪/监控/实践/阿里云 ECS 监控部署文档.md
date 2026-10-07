---
publish: true
tags:
  - 部署
---
> 监控栈运行在普罗米修斯主节点（8.163.97.193），采集生产ECS的系统指标。


---

## 环境信息

| 节点 | 公网IP | 内网IP | 角色 |
|----|----|----|----|
| 普罗米修斯主节点 | 8.163.97.193 | 172.25.41.139 | 监控机 |
| 旧demo环境 | 8.138.202.167 | 172.25.41.135 | 被监控，node_exporter 端口 9999 |
| 自动化部署环境 | 8.163.108.36 | 172.25.41.136 | 被监控 |
| 标注平台 | 8.138.146.48 | 172.25.41.137 | 被监控 |
| VPS节点 | 8.222.213.19 | — | 被监控，走公网 |

> 除VPS外，所有通信走内网IP。


---

## 一、监控机部署监控栈

### 1.1 安装 Docker

```bash
apt update && apt install -y docker.io docker-compose-plugin
systemctl enable docker && systemctl start docker
```

### 1.2 创建目录

```bash
mkdir -p /opt/monitoring/prometheus/rules
cd /opt/monitoring
```

### 1.3 编写 Prometheus 配置

```bash
nano /opt/monitoring/prometheus/prometheus.yml
```

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:

  - job_name: "旧demo环境"
    static_configs:
      - targets: ["172.25.41.135:9999"]
        labels:
          instance: "旧demo环境"

  - job_name: "自动化部署环境"
    static_configs:
      - targets: ["172.25.41.136:9100"]
        labels:
          instance: "自动化部署环境"

  - job_name: "标注平台"
    static_configs:
      - targets: ["172.25.41.137:9100"]
        labels:
          instance: "标注平台"

  - job_name: "vps"
    static_configs:
      - targets: ["8.222.213.19:9100"]
        labels:
          instance: "vps"

  - job_name: "prometheus-self"
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          instance: "prometheus-self"

  - job_name: "普罗米修斯"
    static_configs:
      - targets: ["172.25.41.139:9100"]
        labels:
          instance: "普罗米修斯"
```

### 1.4 编写告警规则

```bash
nano /opt/monitoring/prometheus/rules/node.yml
```

```yaml
groups:
  - name: node_alerts
    rules:

      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "实例 {{ $labels.instance }} 下线"
          description: "{{ $labels.instance }} 已超过1分钟无法采集"

      - alert: HighCPU
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.instance }} CPU使用率过高"
          description: "CPU使用率 {{ $value | printf \"%.1f\" }}%，持续5分钟"

      - alert: HighMemory
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.instance }} 内存使用率过高"
          description: "内存使用率 {{ $value | printf \"%.1f\" }}%，持续5分钟"

      - alert: DiskUsageHigh
        expr: (1 - node_filesystem_avail_bytes{fstype!="tmpfs",mountpoint="/"} / node_filesystem_size_bytes{fstype!="tmpfs",mountpoint="/"}) * 100 > 85
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.instance }} 磁盘使用率过高"
          description: "根分区使用率 {{ $value | printf \"%.1f\" }}%"
```

### 1.5 编写 Alertmanager 配置

```bash
nano /opt/monitoring/alertmanager.yml
```

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'dingtalk'

receivers:
  - name: 'dingtalk'
    webhook_configs:
      - url: 'http://172.25.41.139:8060/dingtalk/webhook1/send' #这里建议使用公网IP，无论镜像名还是容器内域名都容易连不上
        send_resolved: true
```

### 1.6 编写钉钉告警模板

```bash
nano /opt/monitoring/template.tmpl
```

```
{{ define "dingtalk.title" }}[{{ if eq .Status "firing" }}🔥 告警{{ else }}✅ 恢复{{ end }}] {{ .GroupLabels.alertname }}{{ end }}

{{ define "dingtalk.content" }}
{{ if gt (len .Alerts.Firing) 0 }}
**🔥 触发告警 {{ .Alerts.Firing | len }} 条**

{{ range .Alerts.Firing }}
**告警名称**：{{ .Labels.alertname }}

**告警级别**：{{ .Labels.severity }}

**告警主机**：{{ .Labels.instance }}

**告警详情**：{{ .Annotations.description }}

**触发时间**：{{ dateInZone "2006.01.02 15:04:05" .StartsAt "Asia/Shanghai" }}

{{ end }}
{{ end }}
{{ if gt (len .Alerts.Resolved) 0 }}
**✅ 已恢复 {{ .Alerts.Resolved | len }} 条**

{{ range .Alerts.Resolved }}
**告警名称**：{{ .Labels.alertname }}

**告警主机**：{{ .Labels.instance }}

**恢复时间**：{{ dateInZone "2006.01.02 15:04:05" .EndsAt "Asia/Shanghai" }}

{{ end }}
{{ end }}
{{ end }}
```

### 1.7 编写钉钉转发配置

```bash
nano /opt/monitoring/dingtalk.yml
```

```yaml
templates:
  - /etc/dingtalk/template.tmpl

targets:
  webhook1:
    url: <钉钉Webhook地址>
    message:
      msgtype: markdown
      title: '{{ template "dingtalk.title" . }}'
      text: '{{ template "dingtalk.content" . }}'
```

> 钉钉机器人安全模式选「IP白名单」，填监控机公网IP `8.163.97.193`。

### 1.8 编写 docker-compose.yml

```bash
nano /opt/monitoring/docker-compose.yml
```

```yaml
services:

  prometheus:
    image: prom/prometheus:v3.4.0
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/rules:/etc/prometheus/rules
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"

  grafana:
    image: grafana/grafana:11.6.3
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

  alertmanager:
    image: prom/alertmanager:v0.28.1
    container_name: alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - "--config.file=/etc/alertmanager/alertmanager.yml"

  dingtalk:
    image: timonwong/prometheus-webhook-dingtalk:v2.1.0
    container_name: dingtalk
    restart: unless-stopped
    ports:
      - "8060:8060"
    volumes:
      - ./dingtalk.yml:/config/config.yml
      - ./template.tmpl:/etc/dingtalk/template.tmpl
    command:
      - "--web.listen-address=:8060"
      - "--config.file=/config/config.yml"

volumes:
  prometheus-data:
  grafana-data:
```

### 1.9 启动

```bash
cd /opt/monitoring
docker compose up -d
docker compose ps
```


---

## 二、各节点安装 node_exporter

监控机自身和所有生产ECS都需要安装，SSH 进去执行：

```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.8.2/node_exporter-1.8.2.linux-amd64.tar.gz
tar xvf node_exporter-*.tar.gz
mv node_exporter-*/node_exporter /usr/local/bin/
rm -rf node_exporter-*

cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=root
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
```

> 旧demo环境 9100 端口被占用，启动时追加参数： `ExecStart=/usr/local/bin/node_exporter --web.listen-address=:9999`

验证：

```bash
curl http://localhost:9100/metrics | head -3
# curl: (23) 报错是 head 截断导致的，不影响
```


---

## 三、安全组配置

### 监控机入方向

| 端口 | 来源 | 说明 |
|----|----|----|
| 3000 | 0.0.0.0/0 | Grafana Web UI |
| 9090 | VPC内网段 | Prometheus |
| 9093 | VPC内网段 | Alertmanager |

### 各生产ECS入方向

| 端口 | 来源 | 说明 |
|----|----|----|
| 9100 | 172.25.41.139 | node_exporter，仅监控机可访问 |

> VPS节点额外需要在系统防火墙放行9100： `firewall-cmd --permanent --add-port=9100/tcp && firewall-cmd --reload`


---

## 四、配置 Grafana

### 4.1 登录

浏览器访问 `http://8.163.97.193:3000`，默认账密 `admin / admin`，首次登录强制修改密码。

### 4.2 添加 Prometheus 数据源

Settings → Data Sources → Add data source → Prometheus

* URL 填：`http://172.25.41.139:9090`
* 点 **Save & Test**，显示绿色即成功

### 4.3 导入社区 Dashboard

Dashboards → Import，输入 ID：

| Dashboard | ID |
|----|----|
| Node Exporter Full | `1860` |


---

## 五、验证

```bash
# 在监控机上测试各节点连通性
curl http://172.25.41.135:9999/metrics | head -3
curl http://172.25.41.136:9100/metrics | head -3
curl http://172.25.41.137:9100/metrics | head -3
curl http://8.222.213.19:9100/metrics | head -3
```

浏览器访问 `http://8.163.97.193:9090/targets`，所有 target 状态应为 `UP`。


---

## 附：数据持久化

```bash
# 实际数据路径
/var/lib/docker/volumes/monitoring_prometheus-data/_data
/var/lib/docker/volumes/monitoring_grafana-data/_data
```

重建容器不丢数据，迁移时备份上述目录即可。

## 附：重置历史数据

修改 job_name 等 label 后旧数据会残留，清除方式：

```bash
cd /opt/monitoring
docker compose down
docker volume rm monitoring_prometheus-data
docker compose up -d
```