---
publish: true
tags:
  - homelab
  - 运维手册
  - OpenList
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/openlist/` · 重要性：**核心**
> 服务总表见 [[03-服务清单]]

## 1. 这是什么

网盘/存储聚合（AList 的社区分支），把本地磁盘和各种网盘挂成一个统一的文件浏览界面。

- 内网：`http://192.168.31.1:5244`
- 公网：经 ECS nginx → frp `openlist`（ECS 端口 5244）→ docker-host:5244，见 [[阿里云 ECS + FRP + Nginx 公网服务部署 SOP]]
- 2026-10-07 前 ECS 安全组曾放行 5244，可以绕过 HTTPS 直接用明文 HTTP 访问，已关闭

## 2. 部署信息

`/root/openlist/docker-compose.yml`（2026-10-07 修正了数据目录挂载，见第 6 节）：

```yaml
services:
  openlist:
    image: 'openlistteam/openlist:latest'
    container_name: openlist
    user: '0:0'
    volumes:
      - './data:/opt/openlist/data'
      - '/mnt/openlist:/mnt/openlist'
    ports:
      - '5244:5244'
    environment:
      - UMASK=022
    restart: always
```

## 3. 数据

| 内容 | 位置 | 说明 |
|---|---|---|
| 配置 `config.json`、数据库 `data.db`（2 个用户、1 个存储挂载） | `/root/openlist/data/`（挂到容器的 `/opt/openlist/data`） | 不可替代 |
| 本地存储 | `/mnt/openlist`（sdc，直通的 HGST 750G 2.5 寸机械盘，**NTFS**，约 443G 已用） | 不在 VM 系统盘上 |

## 4. 日常操作

```bash
cd /root/openlist
docker logs --since 1h openlist
docker exec openlist ./openlist admin       # 查看/重置管理员信息
```

## 5. 重建

1. 确认 sdc 还在、`/mnt/openlist` 已挂载（NTFS，`fuseblk`）
2. 恢复 compose（第 2 节），`docker compose up -d`
3. 配置丢了：用 `docker exec openlist ./openlist admin set <新密码>` 设管理员密码，再在 Web 端重新添加存储（本地存储路径 `/mnt/openlist`）

## 6. 已知问题与风险

**数据目录挂错了路径（2026-10-07 已修正）**

镜像声明的数据目录是 `/opt/openlist/data`，原来的 compose 却把 `./data` 挂到了 `/root/openlist/data`（AList 时代的旧路径）。结果：

- 真正的配置一直写在 Docker 自动创建的**匿名卷**里，`./data` 是空的
- 平时 `docker compose up -d` 重建容器时，Compose 会沿用旧的匿名卷，所以一直没出问题
- 但只要 `docker compose down` 再 `up`，就会换成一个新的空卷——**管理员账号和所有存储挂载配置全部丢失**

修正过程（以后遇到同类问题照做）：

```bash
cd /root/openlist
docker cp openlist:/opt/openlist/data/. ./data/
# compose 里改成：
#   - './data:/opt/openlist/data'
docker compose up -d
docker exec openlist ls /opt/openlist/data     # 确认 config.json、data.db 都在
# 确认无误后清理旧匿名卷：docker volume rm <旧匿名卷名>
```

2026-10-07 实际执行：拷出的 `data.db` 与原卷校验和一致；重建后存储挂载和用户都在，日志没有"新建管理员"，确认不是重新初始化；旧匿名卷已删除。

> 判断方法：`docker image inspect <镜像> -f '{{json .Config.Volumes}}'` 看镜像声明的数据目录，和 compose 的挂载目标对比；`docker inspect <容器>` 里出现名字是一长串哈希的 volume，通常就是挂错了。

**其他**

- 以 `user: 0:0`（root）运行，`/mnt/openlist` 是 NTFS，Linux 权限位对它无效
- 公网可访问，确认管理员密码足够强、关闭游客访问
