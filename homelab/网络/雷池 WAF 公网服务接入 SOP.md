---
publish: true
tags:
  - 部署
  - WAF
  - Nginx
  - FRP
---

# 雷池 WAF 公网服务接入 SOP

## 目标与范围

本文记录在阿里云 ECS 上将 HTTP/HTTPS 服务接入雷池的方法。ECS Nginx 继续管理 TLS 证书，雷池位于 Nginx 与 FRP 上游之间。下文以已验证接入的 ShiftBalance 为例；其他 Nginx 虚拟主机按相同链路逐个接入。

```text
公网浏览器
  → 域名解析到 ECS
  → ECS Nginx（80/443，acme.sh 管理证书）
  → ECS 本机 127.0.0.1:18080（雷池 HTTP 监听）
  → ECS FRP 服务端的业务远程端口
  → 内网 frpc
  → 内网 Web 应用
```

雷池是 HTTP/HTTPS 反向代理 WAF。原生 TCP/UDP 服务不经过这条链路。

## 部署位置与网络

当前 SafeLine Compose 项目位于 `/root/workspace/safeline`，`.env` 中的 `SAFELINE_DIR` 指向 `/data/safeline`。`safeline-tengine` 使用 host 网络，Nginx 与它共享 ECS 的端口空间；`safeline-mgt` 位于 SafeLine Docker bridge 网络。

因此：

- Nginx 保留公网 `80/443` 和现有 TLS 证书。
- 雷池站点使用 HTTP，并监听一个不冲突的 ECS 本机端口，本部署使用 `18080`。
- ECS 安全组不开放 `18080`，Nginx 通过 `127.0.0.1:18080` 本机访问雷池。
- 雷池上游使用 ECS 上可从 SafeLine 网络访问的宿主机地址和 FRP 远程端口。

## 创建雷池防护站点

在雷池控制台为每个 Web 服务创建一个站点：

1. 填写网站域名。
2. 选择 HTTP，监听端口填写 `18080`。Nginx 已经终止公网 TLS，因此此处不启用 HTTPS，也不需要在雷池重复配置证书。
3. 上游地址填写 `http://<ECS 宿主机网关地址>:<FRP 远程端口>`。
4. 保存后使用雷池站点测试和访问统计确认请求命中。

### 上游地址不能填 localhost

创建 ShiftBalance 站点时曾返回：

```text
invalid upstream http://localhost:8082:
management target "localhost" is not allowed
```

SafeLine 管理端会拒绝 `localhost`；并且容器里的 `localhost` 指向容器本身，不代表 ECS 宿主机。查询 SafeLine bridge 网络的网关地址，并使用这个宿主机可达地址作为上游主机名：

```bash
docker network inspect safeline-ce
```

在输出的 `IPAM.Config` 中查看 `Gateway`。例如 ShiftBalance 的上游格式为：

```text
http://<上一步查到的宿主机网关地址>:8082
```

不要把实际 ECS 公网 IP、私网地址或证书凭据写入公开知识库。

## Nginx 接入雷池

保留现有 Nginx 的 HTTP 跳转和 HTTPS 虚拟主机。将各站点 HTTPS server 中的 `proxy_pass` 指向雷池本机监听端口：

这里的 `18080` 是 Nginx 的反代目标端口；公网 `listen 80/443` 和 TLS 证书保持不变。

```nginx
location / {
    proxy_pass http://127.0.0.1:18080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}
```

在雷池全局配置中将源 IP 获取方式设为从 `X-Real-IP` Header 获取；Nginx 会把它设置为 `$remote_addr`。如果前方另有可信 CDN 或负载均衡器，应先配置可信来源，再传递其提供的真实客户端地址。

逐个站点修改并验证：

```bash
nginx -t && systemctl reload nginx
```

变更后的链路应为：Nginx HTTPS 虚拟主机 → `127.0.0.1:18080` → 雷池站点 → 对应 FRP 上游端口。不要把上游配置回 Nginx 自己的公网域名或 `80/443`，以免形成反代环路。

## 阿里云安全组

安全组只允许所需的公网入口：

- `80/TCP`：用于 HTTP 跳转到 HTTPS。
- `443/TCP`：公网 HTTPS 入口。
- `9443/TCP`：雷池管理端，仅允许管理来源访问。
- `18080/TCP`：不开放公网入站。
- 各 Web 应用对应的 FRP 远程端口：不开放公网入站。
- FRP 控制端口按实际需求限制来源。

关闭 `18080` 的公网安全组入站不会影响 Nginx 到 `127.0.0.1:18080` 的本机连接；同时关闭 FRP Web 端口的公网入站，避免绕过雷池直连上游。

## 数据目录与 PostgreSQL 认证故障

本次首次启动时，`safeline-luigi` 和 `safeline-mgt` 因 PostgreSQL 密码认证失败而反复重启。原因是旧的 `/data/safeline` 数据目录仍保留着旧 PostgreSQL 状态。Docker Compose 的环境变量不会自动修改已初始化数据库中的角色密码。

如果确认需要全新初始化且旧雷池配置、证书和日志都不需要，先停止服务并备份旧数据目录，再让新实例初始化：

```bash
cd /root/workspace/safeline
docker compose down
backup="/data/safeline.backup-$(date +%Y%m%d-%H%M%S)"
mv /data/safeline "$backup"
docker compose up -d
docker compose ps
```

目录备份用于保留旧状态以便回查或恢复。Compose 使用的绑定挂载目录在缺失时可能会随容器启动重新创建；新目录不代表旧数据库状态已恢复。不要在需要保留现有站点配置时删除或移动该目录。检查启动失败原因时查看对应容器日志：

```bash
docker logs --tail 100 safeline-luigi
docker logs --tail 100 safeline-mgt
docker logs --tail 100 safeline-pg
```

## 验证

先从 ECS 验证雷池监听和站点上游：

```bash
curl -i --max-time 5 \
  -H 'Host: <网站域名>' \
  http://127.0.0.1:18080/
```

再验证 Nginx 到雷池的完整路径：

```bash
curl -k -sS -o /dev/null -w 'HTTP %{http_code}\n' \
  --resolve <网站域名>:443:127.0.0.1 \
  https://<网站域名>/
```

响应应符合应用预期，雷池站点访问量应增加。完成后从公网确认 HTTPS 正常，并确认安全组没有开放 `18080` 和对应 FRP Web 端口。

## 常见故障

| 现象 | 处理 |
|---|---|
| 创建站点返回 `localhost is not allowed` | 将上游主机改为 SafeLine bridge 的宿主机网关地址，不使用 `localhost` 或 `127.0.0.1`。 |
| 雷池站点返回 `502` | 检查 FRP 隧道和远程端口；从 ECS 测试对应 FRP 端口，再检查雷池上游地址。 |
| Nginx 返回 `502` | 检查雷池是否监听 `18080`，并在 ECS 测试 `127.0.0.1:18080`。 |
| 添加 HTTPS 站点时要求上传证书 | 当前架构由 Nginx 终止 TLS；将雷池站点设为 HTTP。 |
| 数据库认证失败并导致组件重启 | 检查是否误复用了旧的 `/data/safeline` 数据目录，并核对 PostgreSQL 与应用凭据状态。 |

