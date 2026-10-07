---
publish: true
tags:
  - homelab
  - 部署
---
> 部署在 LXC 101 (docker-host)，通过 LXC 103 Nginx 反代暴露为 `terminal.home`


---

## 环境信息

| 组件 | IP | 说明 |
|----|----|----|
| LXC 101 (docker-host) | 192.168.31.4 | Nexterm 运行位置 |
| LXC 103 (堡垒机) | 192.168.31.6 | Nginx 反代 |


---

## 一、LXC 101 部署 Nexterm

### 创建目录

```bash
mkdir -p /opt/nexterm
cd /opt/nexterm
```

### 编写 docker-compose.yml

```bash
nano docker-compose.yml
```

```yaml
services:
  nexterm:
    image: germannewsmaker/nexterm:latest
    container_name: nexterm
    network_mode: host
    restart: always
    environment:
      - ENCRYPTION_KEY=b4a8fafc485b6425c1de5956daea544ecb5b169ff88831a127d25a72cc8be02b
    volumes:
      - ./nexterm-data:/app/data
```

### 启动

```bash
docker compose up -d
```

### 验证

```bash
docker compose ps
```

正常应显示 `nexterm` 状态为 `Up`。

浏览器访问 `http://192.168.31.4:6989` 确认可以打开。


---

## 二、LXC 103 配置 Nginx 反代

```bash
nano /etc/nginx/sites-available/terminal.home.conf
```

```nginx
server {
    listen 80;
    server_name terminal.home;

    location / {
        proxy_pass http://192.168.31.4:8288;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> Nexterm 用了 WebSocket，必须带 Upgrade 头，否则终端连接会断。

启用配置：

```bash
ln -s /etc/nginx/sites-available/terminal.home.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```


---

## 三、OpenWRT 添加 DNS 记录

OpenWRT SSH 执行：

```bash
echo "192.168.31.6 terminal.home" >> /etc/hosts
/etc/init.d/dnsmasq restart
```


---

## 四、验证

```bash
# OpenWRT 上验证 DNS
nslookup terminal.home 127.0.0.1

# 浏览器访问
http://terminal.home
```


---

## 五、添加 SSH 会话

进入 Nexterm 界面后：


1. 左侧 **+** 新建连接
2. 填写：
   * 名称：如 `PVE`
   * 类型：`SSH`
   * 主机：`192.168.31.2`
   * 端口：`22`
   * 用户名/密码或密钥
3. 保存后点击即可连接

按此方式把所有 LXC/VM 逐一添加进来，可以分组管理。