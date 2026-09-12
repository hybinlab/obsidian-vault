---
publish: true
tags:
  - homelab
  - 部署
---
# Homepage 部署与恢复手册

# Homepage 部署与恢复手册

> 更新：2026-08-16 · 部署人：Red Queen 位置：docker-host（192.168.31.1）`/root/homepage/`

## 1. 这是什么

自托管导航首页（gethomepage/homepage v2）。聚合 Docker Host 组 8 个服务 + Bastion 组 NexTerm + Online 组 Outline，显示服务链接、Docker 容器状态、Grafana/Prometheus 数据 widget。

**官方资料**：

* 仓库：<https://github.com/gethomepage/homepage>
* 文档：[https://gethomepage.dev/（安装/配置/widgets](https://gethomepage.dev/%EF%BC%88%E5%AE%89%E8%A3%85/%E9%85%8D%E7%BD%AE/widgets) 全在左侧导航）

## 2. 部署信息

* 镜像：`ghcr.io/gethomepage/homepage:latest`（v2.0.0 线）
* 端口：**3001 → 3000**（⚠️ 3000 是 grafana 的，不能用）

**完整 compose（**`**/root/homepage/docker-compose.yml**`：

```yaml

services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    container_name: homepage
    environment:
      # 必须带端口；改为别的主机访问前先改这里，否则 Next.js 403
      HOMEPAGE_ALLOWED_HOSTS: 192.168.31.1:3001
      # root 跑；容器要读 docker.sock 必须 root 或在 docker 组
      PUID: 0
      PGID: 0
    ports:
      - 3001:3000
    volumes:
      - ./config:/app/config          # 配置文件目录（确保存在）
      - /var/run/docker.sock:/var/run/docker.sock:ro   # Docker 集成（可选但推荐）
    restart: always
```

要点说明：

* `HOMEPAGE_ALLOWED_HOSTS` 必须与访问地址精确一致（含端口）
* `PUID/PGID=0` = 容器跑 root，docker.sock 和 config 目录都能读写
* 若改回非 root（如 PUID=1000）：需 `chown 1000:1000 config/`，且 docker.sock（660 root:docker）可能读不了，需 `group_add`
* `./config` 目录在首次 up 前确保存在，否则 docker 自动创建且属主可能不匹配

## 3. 配置说明（config/ 目录）

| 文件 | 作用 | 状态 |
|----|----|----|
| `services.yaml` | 服务可见性（组+服务+widget） | 已配好，8+1+1 服务 |
| `docker.yaml` | Docker 实例（my-docker: socket 直连） | 已配好 |
| `settings.yaml` | 全局设置 | 默认模板 |
| `widgets.yaml` | 信息 widget（资源卡/搜索） | 默认模板 |
| `bookmarks.yaml` | 书签 | 空占位 |

**services.yaml 语法要点**：

* 多 widget 必须用**复数** `**widgets:**`（key 数组）；用 `widget:` 数组页面能渲染但数据 API 全 403
* 图标：`sh-xxx` 是 simple-icons 名，或直接 emoji
* widget 类型：docker（容器状态）、grafana（需 username/password）、prometheus（免认证）

## 4. 操作流程

**部署/重启**：

```bash
# docker-host 上
cd /root/homepage && docker compose up -d

docker ps --filter name=homepage   # 应显示 Up (healthy)
```

**改配置后（必做！）**：

```bash

curl http://192.168.31.1:3001/api/revalidate
```

不执行此步，页面会一直显示旧内容（下方坑 1）。

**验证**：

```bash

curl -s -o /dev/null -w "%{http_code}" -H "Host: 192.168.31.1:3001" http://127.0.0.1:3001/   # 期望 200

curl -s -H "Host: 192.168.31.1:3001" "http://127.0.0.1:3001/api/docker/status/homepage/my-docker"  # 期望 running
```

## 5. 恢复手册

| 症状 | 判断 | 处理 |
|----|----|----|
| 页面打不开/容器退出 | 配置 YAML 错误 or 端口冲突 | 先 `docker logs homepage` 看报错；确认 3001 没被占；配置坏了用下方备份回滚 |
| 页面能开但是旧内容 | **不是故障**，是缓存 | `curl /api/revalidate` 刷新（重启无效，缓存落盘） |
| 所有 Docker 状态消失 | socket 权限或 docker.yaml 丢了 | 确认容器以 root 跑（PUID=0）；确认 `docker.yaml` 有 `my-docker: socket: /var/run/docker.sock` |
| widget 报"Unknown proxy service type" | services.yaml 里 widget 键写错 | 检查用的是复数 `widgets:`；检查 widget 类型名拼写 |
| Host 校验 400 | ALLOWED_HOSTS 缺当前访问地址 | 日志会打出被拒 host，把它加进 `HOMEPAGE_ALLOWED_HOSTS`（带端口） |

## 6. 备份清单（回滚用）

| 文件 | 说明 |
|----|----|
| `docker-compose.yml.bak.20260816200842` | 首个可用 compose（改端口/ALLOWED_HOSTS 前） |
| `config.bak.20260816201647/` | 默认模板初版配置 |
| `services.yaml.bak.2026xxxxxx` | 每次改 services.yaml 前的备份（时间戳递增，取最新） |

## 7. 踩坑记录


1. **Next.js 全路由缓存**：v2 首页 `Cache-Control: s-maxage=31536000`（一年）、`x-nextjs-cache: HIT`，改配置后必须 `/api/revalidate`，重启容器不清缓存
2. **multi-widget key 必须是** `**widgets:**` **复数**：单数数组前端能显示、API 全挂，排查耗了半天
3. **ALLOWED_HOSTS 要带端口**：`192.168.31.1:3001` 与 `192.168.31.1` 是两个 host，端口不一致 400
4. **docker.sock 权限**：socket 属 root:docker 660，容器非 root（PUID≠0）且不在 docker 组则读不到
5. **官方文档的** `**HOMEPAGE_ALLOWED_HOSTS: gethomepage.dev**` **是占位示例**，不是可用的部署值