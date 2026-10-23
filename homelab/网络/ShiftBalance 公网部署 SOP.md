---
publish: true
tags:
  - 部署
  - FRP
  - Nginx
---

# ShiftBalance 公网部署 SOP

## 架构

```text
同事浏览器
  → shiftbalance.onecloud.xin:443（ECS Nginx，HTTPS）
  → ECS 本机 127.0.0.1:18080（雷池 WAF，HTTP）
  → ECS FRP 服务端:8082
  → bastion 上的 frpc
  → 应用主机:8082（前端容器）
  → Compose 内部 backend:8080
```

DNS 将域名解析到 ECS。Nginx 继续负责公网 HTTPS 和证书，雷池检查解密后的 HTTP 请求。外部只通过 HTTPS 域名访问；雷池监听端口 `18080` 和 FRP 的 `8082` 端口均不应加入公网安全组入站规则。雷池接入的详细步骤见 [[雷池 WAF 公网服务接入 SOP]]。

## 应用主机

在 ShiftBalance 项目目录维护 `.env`。数据库地址和凭据使用实际环境值，不要提交到 Git 或发布到知识库。

```dotenv
SHIFTBALANCE_DB_URL=jdbc:postgresql://<数据库内网地址>:5432/shiftbalance
SHIFTBALANCE_DB_USER=<数据库用户>
SHIFTBALANCE_DB_PASSWORD=<数据库密码>
SHIFTBALANCE_ADMIN_USERNAME=<初始管理员>
SHIFTBALANCE_ADMIN_PASSWORD=<初始管理员密码>
SHIFTBALANCE_HTTP_PORT=8082
SHIFTBALANCE_CORS_ALLOWED_ORIGINS=https://shiftbalance.onecloud.xin
SHIFTBALANCE_SESSION_COOKIE_SECURE=true
```

Compose 将主机 `8082` 映射到前端容器的 `80` 端口；前端 Nginx 将 `/api` 转发到 Compose 网络中的 `backend:8080`。配置或更新环境变量后重建服务：

```bash
docker compose up -d --build
docker compose ps
```

只修改后端环境变量时：

```bash
docker compose up -d --no-deps --force-recreate backend
```

## FRP 隧道

在 bastion 的 frpc 配置中保留以下代理映射；认证 token 使用已有的安全配置，不写入此文档：

```toml
[[proxies]]
name = "ShiftBalance"
type = "tcp"
localIP = "<应用主机内网地址>"
localPort = 8082
remotePort = 8082
```

重载 frpc 后，确认 ECS 本机可以通过 `127.0.0.1:8082` 访问前端。

## ECS 证书与 Nginx

以下命令以 ECS 上运行 acme.sh 的 root 账户执行。使用已配置的阿里云 DNS API 申请并安装证书；API 凭据保存在 acme.sh 账户配置中，不放入项目或知识库。

```bash
/root/.acme.sh/acme.sh --issue --dns dns_ali \
  -d shiftbalance.onecloud.xin --keylength ec-256

mkdir -p /etc/nginx/ssl/shiftbalance.onecloud.xin
/root/.acme.sh/acme.sh --install-cert \
  -d shiftbalance.onecloud.xin --ecc \
  --cert-file /etc/nginx/ssl/shiftbalance.onecloud.xin/cert.pem \
  --key-file /etc/nginx/ssl/shiftbalance.onecloud.xin/privkey.pem \
  --fullchain-file /etc/nginx/ssl/shiftbalance.onecloud.xin/fullchain.pem \
  --reloadcmd "systemctl reload nginx"
```

在 `/etc/nginx/conf.d/shiftbalance.onecloud.xin.conf` 配置 HTTP 跳转和 HTTPS 反代：

```nginx
server {
    listen 80;
    server_name shiftbalance.onecloud.xin;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name shiftbalance.onecloud.xin;

    ssl_certificate /etc/nginx/ssl/shiftbalance.onecloud.xin/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/shiftbalance.onecloud.xin/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:18080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

```bash
nginx -t && systemctl reload nginx
```

雷池站点监听 HTTP `18080`，上游指向 ECS 上可由雷池容器访问的宿主机网关地址和 FRP 端口 `8082`。创建站点时报 `management target "localhost" is not allowed` 时，不要填写 `localhost` 或 `127.0.0.1`；查询 SafeLine Docker 网络的网关地址并将其用于上游。由于 TLS 已在 Nginx 终止，雷池站点使用 HTTP，不需要再次上传证书。

## 安全组

- `443/TCP`：公网 HTTPS 入口。
- `80/TCP`：仅在需要 HTTP 跳转到 HTTPS 时开放。
- `7000/TCP`：FRP 控制连接，按实际来源限制访问。
- `18080/TCP`：不要开放公网入站；Nginx 通过 ECS 本机回环地址访问雷池。
- `8082/TCP`：不要开放公网入站；雷池在 ECS 本机访问 FRP 服务端。

## 验证

在 ECS 检查 FRP 回源和 Nginx：

```bash
curl -i --max-time 5 http://127.0.0.1:8082/
curl -i --max-time 5 -H 'Host: shiftbalance.onecloud.xin' http://127.0.0.1:18080/
nginx -t
```

从公网检查域名和登录预检：

```bash
curl -I https://shiftbalance.onecloud.xin/

curl -i -X OPTIONS https://shiftbalance.onecloud.xin/api/auth/login \
  -H 'Origin: https://shiftbalance.onecloud.xin' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type,x-csrf-token'
```

页面应返回 `200`，预检响应应包含匹配域名的 `Access-Control-Allow-Origin`。公网直连 `:8082` 应不可达。
公网 HTTPS 访问应经过雷池，且雷池站点访问统计应增加；公网直连 `:18080` 和 `:8082` 应不可达。

## 故障定位

- **Nginx 返回 502**：检查 frpc/frps 连接，并在 ECS 测试 `127.0.0.1:8082`。
- **登录或 CSRF 请求返回 403**：检查 `SHIFTBALANCE_CORS_ALLOWED_ORIGINS` 是否包含完整 HTTPS 来源，然后重建 backend 容器。
- **HTTPS 证书错误**：检查证书安装路径并执行 `nginx -t`；acme.sh 续期安装命令应保留 Nginx reload hook。
