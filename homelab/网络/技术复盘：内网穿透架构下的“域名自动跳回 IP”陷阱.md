---
tags:
  - homelab
  - 复盘
publish: true
---
# 技术复盘：内网穿透架构下的“域名自动跳回 IP”陷阱

## 1. 问题背景

在开发基于 **Proxmox VE** 的虚拟化实训平台时，采用了以下架构：

* **前端**：Vue-Vben-Admin (Docker 容器)
* **后端**：Django + DRF (Docker 容器)
* **网络**：家服 PVE 宿主机 $\xrightarrow{FRP}$ 公网服务器 (106.55.160.167)
* **访问地址**：`http://pve.onecloud.xin`

**故障现象：** 用户通过域名访问并点击"登录"，认证成功后，浏览器地址栏瞬间从域名跳回了家服的公网 IP 或容器映射端口。

## 2. 根因分析：HTTP Host 丢失

问题的本质在于 HTTP 请求头在**四层转发**过程中发生了"信息丢失"。

### 2.1 转发链路分析

请求的原始接力如下：


1. **公网 Nginx**：接收到域名的请求。
2. **FRP 隧道**：将请求打入内网。
3. **内网前端 Nginx (Docker)**：接收请求并代理给后端 Django。
4. **后端 Django**：处理登录并返回 `Redirect`。

### 2.2 逻辑故障点

在默认配置下，每一层反向代理如果没显式声明 `proxy_set_header Host`，Nginx 会将请求头中的 `Host` 改写为 `proxy_pass` 指向的地址（通常是 IP）。

当请求到达 **Django** 时，Django 看到的 `Host` 是前端容器的内部 IP。登录成功后，Django 根据它"感知"到的 Host 生成重定向 Location。浏览器收到这个带 IP 的 Location 后，地址栏便发生了跳转。

## 3. 解决方案（三板斧）

### 第一步：确保公网入口"不掉队"

在公网服务器的 Nginx 配置中，必须使用 `$http_host`（带端口）或 `$host`（不带端口）透传域名。

```nginx
location / {
    proxy_pass http://127.0.0.1:7000; # FRP vhost 端口
    proxy_set_header Host $http_host; # 核心：把域名塞进隧道
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 第二步：确保内网代理"不贪污"

前端 Nginx 容器在转发 `/api` 请求给后端 Django 时，必须继续传递收到的 `Host` 头部，而不是将其改写为后端容器名 `pve_backend`。

```nginx
# Dockerfile 内部 Nginx 配置
location /api/ {
    proxy_pass http://pve_backend:8000/api/;
    proxy_set_header Host $http_host; # 核心：把域名接力给 Django
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 第三步：后端 Django "听指挥"

在 `settings.py` 中开启对转发头的信任。

```python
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

## 4. Nginx 核心知识点复习

这次"坑"提醒我们，复习 Nginx 时要重点关注以下指令：

| 指令 | 作用 | 备注 |
|:---|:---|:---|
| `proxy_set_header Host` | 定义发给后端的 Host 字段 | 默认是 `$proxy_host`，会导致域名丢失 |
| `absolute_redirect off` | 禁止 Nginx 自动补全绝对路径 | 防止 Nginx 擅自将 `/dashboard` 跳到 `http://ip/dashboard/` |
| `port_in_redirect off` | 重定向时不带上内部监听端口 | 避免暴露容器内的 80 端口 |
| `$http_host` vs `$host` | `$http_host` 包含端口号 | 穿透场景下推荐使用 `$http_host` |

## 5. 总结

作为程序员，**"代码没改错，配置毁一生"是常态。在复杂的网络拓扑下，HTTP 协议不再是简单的请求与响应，而是一场跨越多个节点的**接力赛。

**金律：每一层代理都必须像透明玻璃一样，透传** `**Host**`**、**`**IP**` **和** `**Protocol**`**。**


---

**记录日期**：2026-04-25 **状态**：已修复 (Resolved) **后续动作**：全面梳理 PVE 节点的 HTTPS 证书全链路自动化配置。