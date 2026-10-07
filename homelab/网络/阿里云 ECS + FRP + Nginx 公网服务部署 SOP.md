> 日期：2026-09-10
> 背景：把腾讯云 VPS 迁到阿里云 ECS，重建公网 HTTPS 服务链路
> 旧腾讯云方案（仅 frpc，无 nginx/acme）见 [[homelab/网络/frp服务器部署.md]]，已过时，仅作历史参考

---

## 架构目标

```
客户端 → nginx:443 (HTTPS 终止)
           ↓ proxy_pass
         127.0.0.1:<remotePort> (frps 隧道)
           ↓ 隧道
         bastion frpc
           ↓
         docker-host:<localPort> (目标服务)
```

**核心原则：**
- nginx 统一 443，按域名分发
- frps 只占高位端口（5xxx / 6xxx），做纯 TCP 隧道
- 加服务 = nginx 加 server block + frpc 加 proxy，两边解耦

---

## 第一步：前置准备

### 1.1 域名解析

阿里云 DNS 控制台：

| 域名 | 记录类型 | 值 |
|---|---|---|
| nas.onecloud.xin | A | <ECS 公网 IP> |

### 1.2 安全组放行

阿里云 ECS 安全组：

| 端口 | 用途 |
|---|---|
| 443 | HTTPS 入口 |
| 7000 | FRP 控制面 |

### 1.3 服务器准备

```bash
# 创建工作目录
mkdir -p /etc/nginx/ssl/<domain>
```

---

## 第二步：安装 acme.sh（证书管理）

### 2.1 安装

```bash
# 下载并安装（推荐国内源）
curl https://github.com/acmesh-official/acme.sh/archive/refs/tags/3.1.0.tar.gz -o acme.tar.gz
tar -xzf acme.tar.gz
cd acme.sh-3.1.0
./acme.sh --install
source ~/.bashrc
```

### 2.2 配置阿里云 DNS API

阿里云 RAM 控制台创建专门用户：

- 权限：`AliyunDNSFullAccess`（或更细粒度的 DNS 权限）
- 生成 AccessKey ID / Secret

**配置到 acme.sh：**

```bash
export Ali_Key="<AccessKeyId>"
export Ali_Secret="<AccessKeySecret>"
```

> ⚠️ **重要**：acme.sh --issue 成功后会自动把 AK/SK 写入 `~/.acme.sh/account.conf`，后续 --install-cert 不需要再 export。
> 不要在生产 shell 里反复 export，避免泄露到 history。

### 2.3 注册 ZeroSSL 账号（推荐国内 CA）

```bash
~/.acme.sh/acme.sh --register-account -m your@gmail.com --server zerossl
```

### 2.4 申请证书（DNS 验证）

```bash
~/.acme.sh/acme.sh --issue -d <domain> --dns dns_ali
```

**证书生成路径：**

```
~/.acme.sh/<domain>_ecc/
  ├── <domain>.cer        # 证书
  ├── <domain>.key        # 私钥
  ├── fullchain.cer        # 完整链
  └── ca.cer               # 中间 CA
```

---

## 第三步：安装证书到 nginx 路径

```bash
# 创建 nginx 用的目录
mkdir -p /etc/nginx/ssl/<domain>

# 装证书
~/.acme.sh/acme.sh --install-cert -d <domain> --ecc \
  --cert-file /etc/nginx/ssl/<domain>/cert.pem \
  --key-file /etc/nginx/ssl/<domain>/privkey.pem \
  --fullchain-file /etc/nginx/ssl/<domain>/fullchain.pem \
  --reloadcmd "systemctl reload nginx"
```

> ⚠️ **注意一致性**：
> - 如果申请时没加 `--ecc`，安装时也不能加（否则找不到证书）
> - 检查方式：`ls ~/.acme.sh/` 看是 `<domain>/` 还是 `<domain>_ecc/` 目录

---

## 第四步：FRP 服务端配置

### 4.1 安装 frps

```bash
# 下载（GitHub 国内访问慢，用 gh-proxy）
cd /tmp
wget https://gh-proxy.com/https://github.com/fatedier/frp/releases/download/v0.70.1/frp_0.70.1_linux_amd64.tar.gz
tar -xzf frp_0.70.1_linux_amd64.tar.gz -C /usr/local/
mv /usr/local/frp_0.70.1_linux_amd64 /usr/local/frp
cp /usr/local/frp/frps /usr/local/bin/
```

### 4.2 写 frps.toml

```toml
bindPort = 7000
auth.method = "token"          # ⚠️ 字符串必须带引号
auth.token = "IfSsSdETZTG9vrxY"

# dashboard（监听 0.0.0.0 公网可访问，靠 basic auth + 安全组限制来源 IP 保护）
webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "H0melab!2026"
```

**TOML 语法坑：** 字符串值必须带引号 `auth.method = "token"`，否则报 `expected 'true'` 错误。

### 4.3 systemd 服务

```ini
# /etc/systemd/system/frps.service
[Unit]
Description=FRP Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frps -c /etc/frp/frps.toml
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable frps
systemctl start frps
systemctl status frps
```

---

## 第五步：nginx 配置

### 5.1 配置文件

**文件名必须以 `.conf` 结尾**（conf.d 默认只 include `*.conf`）：

```nginx
# /etc/nginx/conf.d/nas.onecloud.xin.conf

server {
    listen 443 ssl;
    server_name nas.onecloud.xin;

    ssl_certificate /etc/nginx/ssl/nas.onecloud.xin/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/nas.onecloud.xin/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:5244;   # FRP 远程端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5.2 nginx 监听 80（certbot / acme 验证）

如果用 certbot 而不是 acme.sh，需要给 80 端口加个最小配置：

```nginx
server {
    listen 80;
    server_name nas.onecloud.xin;
    return 301 https://$host$request_uri;  # 强制 HTTPS
}
```

用 acme.sh + DNS 验证的话，这个不需要。

---

## 第六步：bastion 端 frpc 配置

```toml
# /root/frp/frpc.toml
serverAddr = "<ECS 公网 IP>"
serverPort = 7000
auth.method = "token"
auth.token = "IfSsSdETZTG9vrxY"   # 和 frps 一致

[[proxies]]
name = "openlist"
type = "tcp"
localIP = "<docker-host 内网 IP>"    # 比如 192.168.31.1
localPort = 5244                     # 目标服务的本地端口
remotePort = 5244                    # FRP 在 ECS 上监听的远程端口

# 其他服务按需加：
# [[proxies]]
# name = "calibre"
# type = "tcp"
# localIP = "192.168.31.1"
# localPort = 8083
# remotePort = 8083
```

```bash
systemctl restart frpc
systemctl status frpc
```

---

## 第七步：测试链路

### 7.1 ECS 本地测试

```bash
# frps 是否在监听 5244
ss -tlnp | grep 5244

# 通过 ECS 的 nginx 反代访问
curl -sk https://nas.onecloud.xin | head -5
```

### 7.2 外网测试

Mac 浏览器打开 `https://nas.onecloud.xin`，应该看到服务页面。

---

## 后续加服务的流程

每加一个新服务（比如 PVE、blog）：

```
1. 阿里云 DNS 加一条 A 记录：新域名 → ECS IP
2. acme.sh 申请证书
3. nginx 加一个 server block (新域名，反代到对应端口)
4. frpc 加一个 [[proxies]] (新 localPort → 新 remotePort)
5. 测试链路
```

不需要重启 nginx 或 frps（reload / restart 即可）。

---

## 排障清单

| 症状 | 可能原因 | 排查方法 |
|---|---|---|
| nginx 启动失败 `Address already in use` | 端口被 frps 占 | nginx 改 443，frps 用高位端口 |
| nginx 配置不生效 | 文件名没 `.conf` 后缀 | 重命名为 `domain.conf` |
| nginx 启动后没监听新端口 | systemd 启动早于配置文件创建 | `systemctl restart nginx`（不是 reload） |
| acme.sh 申请证书卡住 | Let's Encrypt 国内访问慢 | 切到 ZeroSSL：`--server zerossl` |
| toml 报错 `expected 'true'` | 字符串没加引号 | `auth.method = "token"` |
| curl 报 `wrong version number` | 端口被占用但服务不是 HTTPS | 检查 ss 看谁占端口 |
| `curl https://domain` 超时 | 防火墙或安全组没放行 | 检查阿里云安全组规则 |

---

## 安全要点

1. **AK/SK 不在 shell history 留痕**——只在交互式 shell 里 export
2. **证书私钥权限** `chmod 600`
3. **frps dashboard 监听 0.0.0.0 + basic auth**——靠用户名密码 + 阿里云安全组限制来源 IP 保护
4. **大端口服务用 frps 转发**——避免直接暴露端口到公网
5. **nginx 443 强制 HTTPS**——用 redirect 而不是可选
6. **SSH 隧道作为备选**——如果 dashboard 不想公网访问，临时改回 `127.0.0.1` + 用 `ssh -L 7500:127.0.0.1:7500 user@host`

---

## 自动化建议

1. **Ansible 模板化 nginx 配置**——加服务时改 inventory 而非手写
2. **Ansible 模板化 frpc.toml**——新机器加入自动生成配置
3. **Prometheus 监控**——nginx_exporter + frps 状态
4. **日志聚合**——Loki 收集 nginx / frp 日志

---

## 参考链接

- [frp GitHub](https://github.com/fatedier/frp)
- [acme.sh GitHub](https://github.com/acmesh-official/acme.sh)
- [nginx 官方文档](https://nginx.org/en/docs/)
- [Let's Encrypt 文档](https://letsencrypt.org/docs/)
