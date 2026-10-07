---
publish: true
tags:
  - homelab
  - 运维手册
  - Calibre-Web
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/calibre-web/` · 重要性：待定（见第 6 节）
> 服务总表见 [[03-服务清单]]

## 1. 这是什么

电子书库的 Web 界面（在线阅读、下载、推送到 Kindle），基于 Calibre 的书库格式。

- 内网：`http://192.168.31.1:8083`
- 公网：经 ECS nginx → frp `calibre`（ECS 端口 8083）→ docker-host:8083

## 2. 部署信息

**不是容器**，是从源码装在 Python 虚拟环境里、由 systemd 管理：

- 源码：`/root/calibre-web`（git clone 自 `github.com/janeczku/calibre-web`，当前 `0.6.26-131-gec521c07`）
- 虚拟环境：`/root/calibre-web/calibre-web-env/`（195M）

`/etc/systemd/system/calibre-web.service`：

```ini
[Unit]
Description=Calibre-Web
After=network.target

[Service]
WorkingDirectory=/root/calibre-web
ExecStart=/root/calibre-web/calibre-web-env/bin/cps
Restart=always

[Install]
WantedBy=multi-user.target
```

没有 `User=`，**以 root 运行**。

## 3. 数据

| 内容 | 位置 | 大小 |
|---|---|---|
| 应用配置、用户（`app.db`）、日志 | `/root/.calibre-web/` | 392K |
| 书库（Calibre 格式，`metadata.db` + 书籍文件） | `/root/calibre-web/library/` | 408K，**0 本书** |

## 4. 日常操作

```bash
systemctl status calibre-web
journalctl -u calibre-web --since "1 hour ago"
tail -f /root/.calibre-web/calibre-web.log

# 升级
cd /root/calibre-web && git pull
calibre-web-env/bin/pip install -r requirements.txt
systemctl restart calibre-web
```

## 5. 重建

1. `git clone https://github.com/janeczku/calibre-web /root/calibre-web`
2. `python3 -m venv calibre-web-env && calibre-web-env/bin/pip install -r requirements.txt`
3. 恢复 systemd unit（第 2 节），`systemctl enable --now calibre-web`
4. 首次登录后在「管理 → 基本配置」里把书库路径设为 `/root/calibre-web/library`

## 6. 已知问题与风险

- **书库是空的（2026-10-07 检查：0 本书）**，却经 frp 暴露在公网上。如果确实不用，建议停掉服务并去掉 frpc 里的 `calibre` 代理，减少一个公网入口；在用的话把重要性改为 core
- 以 root 运行，公网可达，被攻破即 docker-host 的 root 权限
- 书库放在源码目录里，`git pull` 时注意不要被覆盖（目前 `library/` 没有被 git 跟踪）
