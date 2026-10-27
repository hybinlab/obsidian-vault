---
publish: true
---
> ⚠️ **旧版笔记**：这篇是早期腾讯云 VPS（106.55.160.167）上的 frpc 配置，frp 0.54.0/0.65.0。当前用的阿里云 ECS 完整方案（frp 0.70.1 + nginx + acme.sh 证书）见 [[homelab/网络/阿里云 ECS + FRP + Nginx 公网服务部署 SOP.md]]。这篇留着仅作历史参考。

## 1、下载frp源码并上传至服务器

```bash
wget https://github.com/fatedier/frp/releases/download/v0.54.0/frp_0.54.0_linux_amd64.tar.gz

# 下载 FRP（使用 0.54.0 稳定版）
wget https://github.com/fatedier/frp/releases/download/v0.54.0/frp_0.54.0_linux_amd64.tar.gz

# 解压
tar -xzvf frp_0.54.0_linux_amd64.tar.gz

# 进入解压目录
cd frp_0.54.0_linux_amd64

# 查看文件
ls -la
```


或者本地使用scp上传

```bash
scp frp_0.65.0_linux_amd64.tar.gz root@192.168.31.6:/root
```


## **2、创建正确的 frpc.toml 配置文件(直接在frp目录下创建)**

```bash
cat > frpc.toml << 'EOF'
serverAddr = "106.55.160.167"
serverPort = 7000
auth.method = "token"
auth.token = "IfSsSdETZTG9vrxY"

log.to = "./frpc.log"
log.level = "info"
log.maxDays = 3

# 1. PVE 管理界面
[[proxies]]
name = "pve"
type = "tcp"
localIP = "192.168.31.2"
localPort = 8006
remotePort = 8006

# 2. OpenWRT Web 管理
[[proxies]]
name = "openwrtsp"
type = "tcp"
localIP = "192.168.31.3"
localPort = 80
remotePort = 2208

# 3. FRP 容器自身 SSH
[[proxies]]
name = "frp-ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 2209
EOF
```

## **3、 启动 FRP 客户端（测试）**

```bash
# 测试配置
./frpc verify -c ./frpc.toml

# 前台运行（按 Ctrl+C 停止）
./frpc -c ./frpc.toml
```


## 开机自动化脚本

```bash
# 1. 创建 systemd 服务文件
cat > /etc/systemd/system/frpc.service << 'EOF'
[Unit]
Description=FRP Client Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/frp_0.65.0_linux_amd64
ExecStart=/root/frp_0.67.0_linux_amd64/frpc -c /root/frp_0.67.0_linux_amd64/frpc.toml
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# 2. 启用并启动服务
systemctl daemon-reload
systemctl enable frpc
systemctl start frpc

# 3. 检查状态
systemctl status frpc
```


### **📊 端口映射说明**

根据你的配置：

| **服务** | **内网 IP:端口** | **公网访问** | **用途** |
|----|----|----|----|
| PVE | 192.168.31.2:8006 | 106.55.160.167:8006 | PVE 管理界面 |
| OpenWRT | 192.168.31.3:80 | 106.55.160.167:2208 | 路由器管理页面 |
| FRP容器SSH | 127.0.0.1:22 | 106.55.160.167:2209 | SSH 管理容器 |
| docker-host | 192.168.31.4 | 106.55.160.167:2210 | SSH |
