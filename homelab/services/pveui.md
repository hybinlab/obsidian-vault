---
publish: true
tags:
  - homelab
  - 运维手册
  - pveui
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/workspace/pveui/` · 重要性：**核心（毕业设计）**
> 代码和功能说明以仓库 README 为准（`github.com/LSPHYB/pveui`）；本文只记录在 homelab 里**怎么部署、怎么运维**。服务总表见 [[03-服务清单]]

## 1. 这是什么

基于 Django 5 + Vue 3（Vben Admin）的 Proxmox VE 管理与实验教学平台：PVE 节点/虚拟机/LXC/网络拓扑管理、RBAC、实验管理、AI 助手。

- 前端：`http://192.168.31.1:2208`
- 后端 API：`http://192.168.31.1:2209`
- 没有域名、没有公网入口

## 2. 部署信息

仓库里有**两个 compose 文件**，homelab 里用的是 `docker-compose.dev.yml`：

| 文件 | 内容 | 在 homelab 里 |
|---|---|---|
| `docker-compose.yml` | 一体化：自带 MySQL 8 + 后端 + 前端 | ❌ **不要用** |
| `docker-compose.dev.yml` | 后端 + 前端，连外部 MySQL（database `192.168.31.5`） | ✅ 现在运行的就是它 |

```bash
cd /root/workspace/pveui
docker compose -f docker-compose.dev.yml up -d --build
```

> ⚠️ 直接 `docker compose up -d`（不带 `-f`）会用一体化版本，创建自带的 `pve-mysql`；`.env` 里没有填 `MYSQL_ROOT_PASSWORD`，它会无限崩溃重启。2026-10-02 就发生过，一直循环到 10-07 才发现，见 [[容器监控与告警（cAdvisor + Docker 重启次数）]]。

`.env` 里和部署相关的键（值见服务器上的文件）。数据库地址没写在 `.env` 里，用的是 `docker-compose.dev.yml` 里的默认值 `DB_HOST=${DB_HOST:-192.168.31.5}`、`DB_PORT=${DB_PORT:-3306}`：

```ini
DB_NAME=pve
DB_USER=<占位符>
DB_PASSWORD=<占位符>
SECRET_KEY=<占位符>
ADMIN_USERNAME=<占位符>
ADMIN_PASSWORD=<占位符>
BACKEND_PORT=2209
FRONTEND_PORT=2208
REDIS_URL=redis://:<占位符>@192.168.31.6:6379/0   # middleware 的 Redis，Channels 通道层
```

后端启动时会执行 `python manage.py init_rbac --create-superuser`，初始化菜单、权限和超级管理员（已存在时跳过）。

## 3. 数据

| 内容 | 位置 | 说明 |
|---|---|---|
| 业务数据（41 张表：用户、RBAC、PVE 资源、实验、AI 对话等） | database 上的 MySQL 8.4，库 `pve` | **不可替代** |
| 上传文件（头像等） | docker-host 卷 `pveui_media-data`（3.3M） | |
| WebSocket 通道消息 | middleware 的 Redis | 临时数据，丢了无所谓 |
| 代码 | GitHub `LSPHYB/pveui` | ✅ 在 Git 里 |

## 4. 日常操作

```bash
cd /root/workspace/pveui
git pull
docker compose -f docker-compose.dev.yml up -d --build    # 重新构建并部署
docker logs --since 1h django-backend
```

前端是多阶段构建（容器内 `pnpm install && pnpm build:antd`），构建比较慢。

## 5. 重建

1. `git clone` 仓库，恢复 `.env`
2. database 上 MySQL 的 `pve` 库还在：直接 `docker compose -f docker-compose.dev.yml up -d --build`
3. `pve` 库丢了：在 MySQL 上建库和用户，手工导入 `pve.sql`、`seed-menu.sql`（dev 版本不会自动建表），再启动

## 6. 已知问题与风险

- 仓库默认 compose 和 homelab 实际部署方式不一致，容易误用（见第 2 节）；可以考虑在 README 里注明，或把 dev 版本改名为 `docker-compose.homelab.yml`
- 业务库在 database 的 MySQL 上，没有备份
- 2026-10-07 起 WebSocket（Channels）通道层改用 middleware 的 Redis（原来 `REDIS_URL` 为空，用的是进程内存，只能单进程、重启断开所有连接）。为此：
  - `backend/requirements.txt` 加了 `channels-redis==4.3.0`（原镜像里没有这个包，直接填 `REDIS_URL` 会在用到 WebSocket 时报 `ModuleNotFoundError`）——**这处改动还没提交到仓库**
  - Redis 有密码，`REDIS_URL` 里的密码要做 URL 编码
  - 验证：在后端容器里用 `get_channel_layer()` 收发一条消息成功
  - 依赖关系：middleware 的 Redis 挂了，pveui 的实时推送和聊天会失效
