---
publish: true
tags:
  - homelab
  - 运维手册
  - Vaultwarden
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/vaultwarden/` · 重要性：**核心（数据价值最高）**
> 服务总表见 [[03-服务清单]]，HTTPS / DNS 排障见 [[Vaultwarden 内网 HTTPS 反代与 DNS 排障记录]]

## 1. 这是什么

Bitwarden 兼容的自托管密码管理器（Rust 实现，资源占用很小）。客户端用官方 Bitwarden App / 浏览器插件，服务器地址填 `https://vault.onecloud.xin`。

- 访问：`https://vault.onecloud.xin`（经 [[Caddy]]，只能在家访问；Bitwarden 客户端要求 HTTPS）
- 不经过 frp，**没有公网入口**
- 版本：Vaultwarden 1.37.2，Web-Vault 2026.7.0

## 2. 部署信息

`/root/vaultwarden/docker-compose.yml`：

```yaml
services:
  vaultwarden:
    image: vaultwarden/server:latest
    container_name: vaultwarden
    restart: always
    environment:
      - SIGNUPS_ALLOWED=false   # 关闭自助注册(2026-10-07);新账号用邀请或临时打开
    volumes:
      - ./vw-data/:/data/
    ports:
      - 8084:80
```

除关闭注册外，其余全部使用默认配置。需要新增账号时：临时把 `SIGNUPS_ALLOWED` 改成 `true` 并 `docker compose up -d`，注册完改回来。

## 3. 数据

`/root/vaultwarden/vw-data/`，总共约 2M：

| 文件 | 内容 | 重要性 |
|---|---|---|
| `db.sqlite3`（+ `-wal`、`-shm`） | 所有账号、密码库条目（客户端加密后存储） | **不可替代** |
| `rsa_key.pem` | 登录令牌的签名密钥 | 丢了所有客户端需要重新登录 |
| `icon_cache/` | 网站图标缓存 | 可重新获取 |

> 密码库条目在服务端是加密存储的，没有主密码解不开；但**数据库丢了，密码就真的丢了**。
> 客户端（手机、浏览器插件）本地有一份离线缓存，服务器挂了一段时间内仍能查看已同步的密码，但不能新增和同步。

## 4. 日常操作

```bash
cd /root/vaultwarden

docker logs --since 1h vaultwarden          # 看登录、同步
docker compose pull && docker compose up -d # 升级
```

导出一份（不依赖服务器的应急手段）：在 Web 端「工具 → 导出密码库」，选**加密的 JSON** 格式，存到别处。

## 5. 重建

1. 恢复 `docker-compose.yml`（第 2 节）
2. 如果 `vw-data/` 还在：直接 `docker compose up -d`，一切照旧
3. 如果 `vw-data/` 丢了：只能重新注册账号，再从之前导出的文件导入；没有导出就没有办法
4. [[Caddy]] 里 `vault.onecloud.xin` 站点和 OpenWrt 内网解析要在

## 6. 已知问题与风险

- **没有备份**（见 [[04-备份与恢复]]），数据在 docker-host 系统盘（sdd 上的 qcow2）。2M 的数据量，手动定期导出一次加密 JSON 就能覆盖最坏情况。
- 默认允许任何人注册，2026-10-07 已设 `SIGNUPS_ALLOWED=false` 关闭（验证：`POST /identity/accounts/register/send-verification-email` 返回 `Registration not allowed`）。
- **没有管理后台**（没设 `ADMIN_TOKEN`），`/admin` 不可用。需要时再加，token 用 `vaultwarden hash` 生成 Argon2 哈希，不要写明文。
- 镜像用 `latest`，升级前看一眼 release notes。
