---
publish: true
tags:
  - 部署
---
# Prometheus + Grafana 部署文档

> 监控栈运行在 LXC 101 (docker-host)，采集所有 VM 和 LXC 的系统指标。

> ⚠️ 2026-10-07 备注：本文是早期版本的部署记录，IP 和目录已经变化。当前监控栈在 docker-host `192.168.31.1` 的 `/root/monitoring/`，Prometheus 只直接抓 docker-host 的 node_exporter，agent / database / bastion / middleware 都由 Alloy 通过 remote write 推送。现行配置见 [[Prometheus 告警 → ntfy 手机推送]] 和 [[Loki 日志告警与监控组件自监控]]。


---

## 环境信息

| 设备 | IP | 类型 | exporter |
|----|----|----|----|
| PVE 宿主机 | 192.168.31.2 | 裸机 | pve-exporter |
| LXC 101 docker-host | 192.168.31.4 | 特权 LXC | node_exporter + cAdvisor |
| LXC 103 堡垒机 | 192.168.31.6 | 非特权 LXC | node_exporter |
| LXC 106 openclaw | 192.168.31.10 | 非特权 LXC | node_exporter |
| VM 100 OpenWRT | 192.168.31.3 | KVM | 跳过 |
| VM 102 Kali | 192.168.31.x | KVM | node_exporter |
| VM 104 Windows 11 | 192.168.31.x | KVM | windows_exporter |

> LXC 106、VM 102、VM 104 的 IP 替换为实际地址。


---

## 一、LXC 101 部署监控栈

### 1.1 创建目录

```bash
mkdir -p /opt/monitoring/prometheus
cd /opt/monitoring
```

### 1.2 编写 Prometheus 配置

```bash
nano /opt/monitoring/prometheus/prometheus.yml
```

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:

  # PVE 
  - job_name: "pve"
    static_configs:
      - targets: ["192.168.31.2:9221"]
    metrics_path: /pve
    params:
      module: [default]

  # LXC 101
  - job_name: "node-lxc101"
    static_configs:
      - targets: ["192.168.31.4:9100"]

  # LXC 103
  - job_name: "node-lxc103"
    static_configs:
      - targets: ["192.168.31.6:9100"]

  # VM 105
  - job_name: "node-openclaw"
    static_configs:
      - targets: ["192.168.31.10:9100"]

  # VM 102 Kali
  - job_name: "node-kali"
    static_configs:
      - targets: ["192.168.31.5:9100"]

  # VM 104 Windows 11
  - job_name: "node-windows"
    static_configs:
      - targets: ["192.168.31.7:9182"]

  # Docker
  - job_name: "cadvisor"
    static_configs:
      - targets: ["192.168.31.4:8080"]
```

### 1.3 编写 pve-exporter 配置

```bash
nano /opt/monitoring/prometheus/pve.yml
```

```yaml
default:
  user: root@pam
  password: 你的PVE密码
  verify_ssl: false
```

### 1.4 编写 docker-compose.yml

```bash
nano /opt/monitoring/docker-compose.yml
```

```yaml
services:

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

  pve-exporter:
    image: prompve/prometheus-pve-exporter:latest
    container_name: pve-exporter
    restart: unless-stopped
    ports:
      - "9221:9221"
    volumes:
      - ./prometheus/pve.yml:/etc/pve.yml
    command:
      - "--config.file=/etc/pve.yml"

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - "--path.procfs=/host/proc"
      - "--path.sysfs=/host/sys"
      - "--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)"

volumes:
  prometheus-data:
  grafana-data:
```

### 1.5 启动

```bash
cd /opt/monitoring
docker compose up -d
```

验证所有容器启动正常：

```bash
docker compose ps
```


---

## 二、各设备安装 node_exporter

### 2.1 LXC 103、LXC 106、VM 102 (Linux)

每台机器 SSH 进去执行：

```bash
# 下载
wget https://github.com/prometheus/node_exporter/releases/latest/download/node_exporter-1.8.2.linux-amd64.tar.gz

# 解压安装
tar xvf node_exporter-*.tar.gz
mv node_exporter-*/node_exporter /usr/local/bin/

# 创建 systemd 服务
cat > /etc/systemd/system/node_exporter.service << EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=root
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

# 启动并设置开机自启
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
```

验证：

```bash
curl http://localhost:9100/metrics | head -5
```

### 2.2 非特权 LXC 说明

非特权容器 `/proc` 部分路径受限，node_exporter 部分指标（如 `hwmon`）会采集失败，属正常现象，不影响 CPU / 内存 / 磁盘 / 网络核心指标。

### 2.3 VM 104 Windows 11


1. 前往 https://github.com/prometheus-community/windows_exporter/releases 下载最新 `.msi`
2. 双击安装，默认端口 `9182`
3. PowerShell 放行防火墙：

```powershell
netsh advfirewall firewall add rule name="windows_exporter" dir=in action=allow protocol=TCP localport=9182
```


---

## 三、LXC 103 配置 Nginx 反代 Grafana

```bash
nano /etc/nginx/sites-available/grafana.home.conf
```

```nginx
server {
    listen 80;
    server_name grafana.home;

    location / {
        proxy_pass http://192.168.31.4:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/grafana.home.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```


---

## 四、OpenWRT 添加 DNS

```bash
echo "192.168.31.6 grafana.home" >> /etc/hosts
/etc/init.d/dnsmasq restart
```


---

## 五、配置 Grafana

### 5.1 登录

浏览器访问 `http://grafana.home`，默认账密 `admin / admin`，首次登录强制修改密码。

### 5.2 添加 Prometheus 数据源

Settings → Data Sources → Add data source → Prometheus

* URL 填：`http://192.168.31.4:9090`
* 点 **Save & Test**，显示绿色即成功

### 5.3 导入社区 Dashboard

Dashboards → Import，输入 Dashboard ID：

| Dashboard | ID |
|----|----|
| Node Exporter Full | `1860` |
| PVE 监控 | `10347` |
| cAdvisor Docker | `14282`(经测试，这玩意没用) |
| Windows Exporter | `10467` |


---

## 六、验证各 exporter 连通性

在 LXC 101 上逐一测试：

```bash
curl http://192.168.31.6:9100/metrics | head -3      # LXC 103
curl http://192.168.31.x:9100/metrics | head -3      # LXC 106，替换 IP
curl http://192.168.31.x:9100/metrics | head -3      # Kali，替换 IP
curl http://192.168.31.x:9182/metrics | head -3      # Windows 11，替换 IP
curl "http://192.168.31.2:9221/pve?module=default" | head -3  # PVE
curl http://192.168.31.4:8080/metrics | head -3      # cAdvisor
```

浏览器访问 `http://192.168.31.4:9090/targets`，所有 target 状态应为 `UP`。


---

## 附：数据持久化说明

Prometheus 和 Grafana 均使用 Docker named volume，数据由 Docker 统一管理：

```bash
# 查看 volume 详情
docker volume inspect monitoring_prometheus-data
docker volume inspect monitoring_grafana-data

# 实际数据路径
/var/lib/docker/volumes/monitoring_prometheus-data/_data
/var/lib/docker/volumes/monitoring_grafana-data/_data
```

重建容器不会丢失数据，迁移时备份上述目录即可。