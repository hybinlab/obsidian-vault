---
publish: true
tags:
  - homelab
  - 运维手册
  - Jellyfin
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/jellyfin/` · 重要性：**核心**
> 服务总表见 [[03-服务清单]]

## 1. 这是什么

自托管影视媒体服务器（电影、动画等），浏览器或 Jellyfin 客户端访问。

- 访问：`http://192.168.31.1:8096`（只在内网，没有域名、没有公网入口）
- `7359/udp` 是客户端自动发现服务器用的

## 2. 部署信息

`/root/jellyfin/docker-compose.yml`：

```yaml
services:
  jellyfin:
    image: jellyfin/jellyfin
    container_name: jellyfin
    ports:
      - 8096:8096/tcp
      - 7359:7359/udp
    volumes:
      - ./config:/config
      - ./cache:/cache
      - type: bind
        source: /mnt/jellyfin
        target: /media
        read_only: true
    restart: always
```

媒体以**只读**方式挂进容器，Jellyfin 不会改动原始文件。

## 3. 数据

| 内容 | 位置 | 大小 | 说明 |
|---|---|---|---|
| 媒体文件 | `/mnt/jellyfin`（sdb，直通的 WD 1TB 2.5 寸机械盘，ext4） | 约 431G | 不在 VM 系统盘上，sdd 坏了它还在 |
| 配置、用户、观看记录 | `/root/jellyfin/config/`（`data/` 里是数据库） | 75M | 在 docker-host 系统盘 |
| 刮削的元数据（海报等） | `/root/jellyfin/config/metadata/` | 70M | 可重新刮削 |
| 转码缓存 | `/root/jellyfin/cache/` | 5M | 可随时删 |

## 4. 日常操作

```bash
cd /root/jellyfin
docker logs --since 1h jellyfin
docker compose pull && docker compose up -d   # 升级
```

新增媒体：拷贝到 `/mnt/jellyfin/<分类>/`，在 Web 端「控制台 → 媒体库 → 扫描所有媒体库」。

## 5. 重建

1. 确认 sdb 还在、`/mnt/jellyfin` 已挂载（docker-host 的 `/etc/fstab`）
2. 恢复 compose，`docker compose up -d`
3. `config/` 还在：一切照旧；丢了：重新走初始化向导、添加媒体库（路径 `/media/...`），重新刮削

## 6. 已知问题与风险

- **sdb 有坏道迹象**：2026-10-05、10-07 两次读同一扇区失败，日志告警 DiskIOError 会推送，见 [[Loki 日志告警与监控组件自监控]]。sdb 是一块 2.5 寸 5400 转笔记本盘，在 PVE 上 `smartctl -a /dev/sdb` 确认健康度（[[04-备份与恢复]] 待确认项）。
- 媒体没有第二份。
- 镜像没有固定版本（默认 `latest`）。
