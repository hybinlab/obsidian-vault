---
publish: true
tags:
  - 部署
  - homelab
---
# Portainer 部署与恢复手册

# Portainer 部署与恢复手册

> 更新：2026-08-17 · 部署人：用户（Red Queen 协助验收） 位置：docker-host（192.168.31.1）`/root/portainer/`

## 1. 这是什么

Docker/Kubernetes 管理面板（Web UI）。管理 docker-host 全部容器：状态查看、日志、重启、Stack（compose）管理。

**官方资料**：

* 仓库：[https://github.com/portainer/portainer（38.3k](https://github.com/portainer/portainer%EF%BC%8838.3k) stars）
* 文档：<https://docs.portainer.io/>
* 线上地址：<https://192.168.31.1:9443>

## 2. 部署信息

**完整 compose（**`**/root/portainer/docker-compose.yml**`**，可直接复制）**：

```yaml

services:
  portainer:
    container_name: portainer
    image: portainer/portainer-ce:lts
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    ports:
      - 9443:9443
      - 8002:8000  # Edge Agent 通信端口（原 8000 被 cptr 占用，改 8002）

volumes:
  portainer_data:
    name: portainer_data

networks:
  default:
    name: portainer_network
```

要点：

* **9443 = 管理界面（HTTPS）**；**8002 = Edge Agent 通信口**（给边缘 agent 反向连用的，不用 Edge 可去掉）
* 镜像用 `lts` tag（比 latest 稳）
* `portainer_data` 卷 = 全部配置（环境、栈定义、设置），备份/迁移就拷这个卷

## 3. 操作流程

**部署/重启**：

```bash
# docker-host 上
cd /root/portainer && docker compose up -d

docker ps --filter name=portainer   # 应显示 Up
```

**验证**：

```bash

curl -sk -o /dev/null -w "%{http_code}" https://127.0.0.1:9443/   # 期望 200
```

**首次初始化（关键）**：新版（2.39+）首次访问需要 setup token 创建 admin：


1. 看容器日志拿 token：`docker logs portainer | grep setup_token`
2. 浏览器打开 `https://192.168.31.1:9443/?setup-token=<token>` 完成 admin 创建
3. 之后直接 <https://192.168.31.1:9443> 登录

## 4. 恢复手册

| 症状 | 判断 | 处理 |
|----|----|----|
| UI 打不开 | 容器挂了 or 9443 被占 | `docker ps` / `docker logs portainer`；确认 9443 空闲 |
| 忘记 admin 密码 | 无 Web 重置 | 用官方 helper 镜像重置（见下「重置 admin 密码」） |
| 数据全丢 | portainer_data 卷损坏/误删 | 该卷含全部配置；恢复=用卷备份还原（见下） |

**数据备份/迁移**：

```bash
# 备份卷
docker run --rm -v portainer_data:/data -v /root/backups:/backup alpine tar czf /backup/portainer_data_$(date +%Y%m%d).tar.gz -C /data .
# 恢复
docker run --rm -v portainer_data:/data -v /root/backups:/backup alpine tar xzf /backup/portainer_data_xxx.tar.gz -C /data
```

## 4.5 重置 admin 密码（官方 helper，2026-08-19 实测）


1. 停容器（防数据卷 DB 写入冲突）：

```bash

docker stop portainer
```


2. 跑官方 helper 镜像，挂载同一个数据卷，重设 admin 密码（`--password` 给明文新密码）：

```bash

docker run --rm -v portainer_data:/data portainer/helper-reset-password --password "你的新密码"
# 不带 --password 则生成随机密码并打印到 stdout
```


3. 启动容器：

```bash

docker start portainer
```


4. 用 `admin` + 新密码登录 <https://192.168.31.1:9443>

原理：admin 及密码 bcrypt hash 存于 `portainer_data` 卷内的数据库中，helper 容器挂同一卷原地改写 hash，不丢其它配置。官方文档：<https://docs.portainer.io/advanced/reset-admin>

## 5. 踩坑记录


1. **Edge 端口默认 8000**：docker-host 的 8000 已被 cptr（OpenWebUI Computer）占用，必须改宿主映射端口（用 8002），容器内 8000 不变
2. **9443 vs 8002 分工**：9443 是 UI，8002 是 Edge Agent 通道——别拿 8002 当管理入口
3. **首次初始化 token 机制**：2.39+ 安全增强，没有 token 无法创建 admin；token 只首次有效，在容器日志里