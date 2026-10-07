---
publish: true
tags:
  - homelab
  - 运维手册
  - Caddy
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/caddy/` · 重要性：**基础设施**
> 服务总表见 [[03-服务清单]]，排障记录见 [[Vaultwarden 内网 HTTPS 反代与 DNS 排障记录]]

## 1. 这是什么

内网 `*.onecloud.xin` 的 HTTPS 入口。证书用 **阿里云 DNS 验证**（DNS-01）自动签发和续期，所以内网服务不用暴露到公网也能拿到正式证书。

在家访问的路径：浏览器 → OpenWrt（31.11）DNS 把域名解析到 `192.168.31.1` → Caddy :443 → 后端服务。

| 域名 | 后端 | 服务 |
|---|---|---|
| `vault.onecloud.xin` | `192.168.31.1:8084` | [[Vaultwarden]] |
| `code.onecloud.xin` | `192.168.31.1:8080` | code-server（systemd，root 运行） |
| `karakeep.onecloud.xin` | `192.168.31.1:3002` | [[Karakeep]] |

> 公网访问不走 Caddy，走 ECS nginx → frp，见 [[阿里云 ECS + FRP + Nginx 公网服务部署 SOP]]。

## 2. 部署信息

官方镜像不带阿里云 DNS 插件，所以用 `xcaddy` 自己编译：

`/root/caddy/Dockerfile`：

```dockerfile
FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/alidns

FROM caddy:2

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

`/root/caddy/docker-compose.yml`：

```yaml
services:
  caddy:
    build: .
    image: caddy-alidns:latest
    restart: always
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    env_file:
      - .env
    volumes:
      - ./conf:/etc/caddy
      - ./site:/srv
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
```

`/root/caddy/conf/Caddyfile`（每个站点结构相同）：

```caddy
vault.onecloud.xin {
    tls {
        dns alidns {
            access_key_id {env.ALIYUN_ACCESS_KEY_ID}
            access_key_secret {env.ALIYUN_ACCESS_KEY_SECRET}
        }
    }
    reverse_proxy 192.168.31.1:8084
}
```

`/root/caddy/.env`（权限 600）：

```ini
# 阿里云 RAM AccessKey(DNS 解析权限),Caddy 用来做 DNS-01 证书验证
ALIYUN_ACCESS_KEY_ID=<占位符>
ALIYUN_ACCESS_KEY_SECRET=<占位符>
```

当前版本：Caddy v2.11.4。

## 3. 数据

| 内容 | 位置 | 说明 |
|---|---|---|
| 配置 | `/root/caddy/conf/Caddyfile` | **不在 Git、没有其他副本**；丢了按本文第 2 节重写 |
| 证书和 ACME 账号 | 卷 `caddy_caddy_data`（164K） | 丢了没关系，启动后自动重新申请 |
| 阿里云 AccessKey | `/root/caddy/.env`（600） | 不在知识库里，丢了到阿里云 RAM 重新创建 |

## 4. 日常操作

```bash
cd /root/caddy

# 加一个站点：编辑 conf/Caddyfile，复制一段改域名和后端，然后热加载（不中断服务）
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# 看证书申请/续期
docker logs --since 24h caddy 2>&1 | grep -iE 'certificate|renew|error'

# 升级（重新编译）
docker compose build --pull && docker compose up -d
```

新站点还要在 OpenWrt 上加内网解析（`<子域>.onecloud.xin` → `192.168.31.1`），否则在家访问不到。

## 5. 重建

1. 按第 2 节恢复 `Dockerfile`、`docker-compose.yml`、`conf/Caddyfile`
2. 填入阿里云 AccessKey（需要 DNS 解析权限）
3. `docker compose up -d --build`，看日志确认各域名证书签发成功

## 6. 已知问题与风险

- 阿里云 AccessKey 原先明文写在 compose 的 `environment` 里，2026-10-07 已挪到 `.env`（600）。旧的 `docker-compose.yml.bak.*` 里仍有明文，已改为 600；不需要时可以删掉。这把 key 有 DNS 解析权限，建议在阿里云 RAM 里确认它只有 `AliyunDNSFullAccess`。
- Caddy 挂了 = 所有内网域名都打不开（各服务的 IP:端口 直连仍可用）。目前没有针对 Caddy 的单独告警，容器停止会由 ContainerDisappeared 发现，见 [[容器监控与告警（cAdvisor + Docker 重启次数）]]。
- `code.onecloud.xin` 后面是**以 root 运行的 code-server**，等于一个浏览器里的 root shell，只能在内网用，不要加到 frp。
