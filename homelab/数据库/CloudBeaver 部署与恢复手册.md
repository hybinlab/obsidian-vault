---
publish: true
tags:
  - homelab
  - 部署
---
# CloudBeaver 部署与恢复手册

> 更新：2026-08-17 · 部署人：Red Queen（用户指挥，二次重构定稿） 位置：docker-host（192.168.31.1）`/root/cloudbeaver/`

## 1. 这是什么

Web 版数据库管理工具（DBeaver 的 Web 形态）。浏览器里管 MySQL/PostgreSQL：SQL 编辑器、表浏览、ER 图、连接管理。

**官方资料**：

* 仓库：[https://github.com/dbeaver/cloudbeaver（5.1k](https://github.com/dbeaver/cloudbeaver%EF%BC%885.1k) stars）
* 文档：<https://github.com/dbeaver/cloudbeaver/wiki>
* 线上地址：<http://192.168.31.1:8978>

## 2. 部署信息

**最终形态：社区版单容器**（无 nginx 反代、无自带数据库）。完整 compose（`/root/cloudbeaver/docker-compose.yml`）：

```yaml

services:
  cloudbeaver:
    image: dbeaver/cloudbeaver:latest
    restart: unless-stopped
    ports:
      - "0.0.0.0:8978:8978"
    environment:
      CLOUDBEAVER_DB_DRIVER: postgres-jdbc
      CLOUDBEAVER_DB_URL: jdbc:postgresql://192.168.31.5:5432/cloudbeaver
      CLOUDBEAVER_DB_USER: cloudbeaver
      CLOUDBEAVER_DB_PASSWORD: ${CLOUDBEAVER_DB_PASSWORD}
      CLOUDBEAVER_DB_SCHEMA: cb
    volumes:
      - cloudbeaver_data:/opt/cloudbeaver/workspace

volumes:
  cloudbeaver_data:
```

同目录 `.env` 提供 `CLOUDBEAVER_DB_PASSWORD`（compose 自动读取，密码不硬编码）。

要点：

* **元数据库 = 自家 PG**（192.168.31.5:5432/cloudbeaver，用户 `cloudbeaver`）——CloudBeaver 的连接配置/用户/权限都存这，`cb_` schema 51 张表
* `cloudbeaver_data` 卷 = workspace（工作区文件，非元数据）
* 社区版 26.x 支持外部元数据库，`CLOUDBEAVER_DB_*` 变量**生效**（老文档说 EE 专属，已过时）

## 3. 操作流程

**部署/重启**：

```bash
# docker-host 上
cd /root/cloudbeaver && docker compose up -d

docker ps --filter name=cloudbeaver   # 应显示 Up
```

**验证**：

```bash

curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8978/   # 期望 200
# 数据库连接日志（关键确认）：
docker logs dbeaver-cloudbeaver-1 | grep -E "management database|connection established"
```

## 4. 恢复手册

| 症状 | 判断 | 处理 |
|----|----|----|
| 页面打不开 | 容器挂/端口冲突 | `docker ps` / `docker logs dbeaver-cloudbeaver-1`；确认 8978 空闲 |
| 登录后连接不到库 | 目标库不可达/凭据错 | 先在 CloudBeaver 里测试连接；再检查 PG 可达性与凭据（见下） |
| 忘记 admin 登录密码 | 无 Web 重置 | 删 serverName 走向导重设（见 4.5，连接/设置保留） |
| 元数据损坏 | 31.5 PG 的 cloudbeaver 库出问题 | 该库是全部连接配置，恢复=PG 备份还原（pg_dump 惯例） |
| 想整体重置 | 配置全乱 | down + 删 cloudbeaver_data 卷 + 重建 PG 库（`DROP/CREATE DATABASE cloudbeaver`），再从零初始化 |

**PG 元数据库访问**：

```bash
# 用户 cloudbeaver / 密码在 .env

PGPASSWORD=$(grep CLOUDBEAVER_DB_PASSWORD .env | cut -d= -f2) \
  psql -h 192.168.31.5 -U cloudbeaver -d cloudbeaver
```

## 4.5 重置 admin 登录密码（删 serverName → 向导，2026-08-19 实测，官方推荐）


1. 删掉 CloudBeaver 判断"是否已初始化"的 serverName 行（容器内）：

```bash

docker exec dbeaver-cloudbeaver-1 sh -c \
  "cp /opt/cloudbeaver/workspace/.data/.cloudbeaver.runtime.conf \
      /opt/cloudbeaver/workspace/.data/.cloudbeaver.runtime.conf.bak2 && \
   sed -i 's/    \"serverName\": \"cloudbeaver\",//' \
      /opt/cloudbeaver/workspace/.data/.cloudbeaver.runtime.conf"
```


2. 重启容器：

```bash

docker restart dbeaver-cloudbeaver-1
```


3. 浏览器访问 <http://192.168.31.1:8978> → 自动进**设置向导**，重设 admin 密码
4. **已配置的数据源连接 / license / 其它设置全部保留**（不依赖 serverName）

⚠️ 不要直接改 `cb.cb_user_credentials.cred_value`（认证 hash 非标准 bcrypt，硬改有锁死风险）；官方方案就是删 serverName 走向导。官方文档：<https://dbeaver.com/docs/cloudbeaver/Admin-Password-Recovery>

## 5. 踩坑记录


1. **别用 EE 全家桶**：官方部署包（web-proxy + cloudbeaver-ee + 自带 postgres）对单机是杀鸡用牛刀——社区版单容器自带内嵌 web server，一套 compose 完事（EE 容器已删，`dbeaver_*` 旧卷可清）
2. **端口绑定**：`127.0.0.1:8978` 只本机可访问，局域网要用 `0.0.0.0:8978:8978`
3. `**CLOUDBEAVER_DB_\***` **社区版生效**（26.x）：外部 PG 可当元数据库；设了变量但看不到效果时，日志 `grep management database` 确认
4. **ClickHouse 驱动警告无害**：可选驱动缺 jar，不影响主功能
5. **EE 镜像无 license 的 "No active license" 警告正常**：跑的就是社区功能

---

## 相关笔记

- [[homelab/数据库/MySQL 8.4 二进制安装.md]]
- [[homelab/数据库/PostgreSQL_的详细安装方式（全平台覆盖).md]]