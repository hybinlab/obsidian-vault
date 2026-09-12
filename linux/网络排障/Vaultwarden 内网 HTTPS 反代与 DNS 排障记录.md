---
tags:
  - linux
  - 排障
publish: true
---
# Vaultwarden 内网 HTTPS 反代与 DNS 排障记录（POC）

> 日期：2026-08-24 场景：自托管 Vaultwarden 需要 HTTPS，homelab 内网访问 状态：✅ 已解决，可复用


---

## 一、问题

### 1.1 需求和约束

* Vaultwarden（Bitwarden 兼容服务端）**强制要求 HTTPS**（其前端依赖 Subtle Crypto API，浏览器仅安全上下文可用）
* homelab 内网：OpenWrt 网关（192.168.31.11）+ OpenClash（Meta 内核，**fake-ip 模式**）
* 域名：`onecloud.xin`（阿里云 DNS 托管），公网资产指向 TCP VPS `106.55.160.167`
* 结论诉求：内网设备纯内网访问，不含手机流量

### 1.2 现象

* 直接 HTTP 访问 `http://192.168.31.1:8084` → 页面报「您需要启用 HTTPS！」
* 浏览器访问 `https://vault.onecloud.xin` → 「无法访问此网站」（Chrome 电脑/手机均失败）
* 个别通道（微信内置浏览器）却能打开

### 1.3 关键误区

> 曾以为 `部分浏览器能访问、部分不能` 是**证书问题** —— 实际证书完全正常（Let's Encrypt 真证书，`Verify return code: 0`）。真正的病根在 **DNS 解析层**。


---

## 二、解决思路（分层排障，先现象→后根因）

### 2.1 拆解「HTTPS 从输入到打开」涉及哪些独立环节

访问 `https://vault.onecloud.xin/` 要同时满足：

```
1. 证书有效且域名匹配（vault.onecloud.xin 在 SAN 里）
2. DNS 能把 vault.onecloud.xin 解析到内网 IP（192.168.31.1）
3. 反代（Caddy）把 443 → 后端 vaultwarden（8084）
4. 网络路径可达
```

**任何一个断了就打不开**。必须逐个环节独立验证，不能笼统归咎"证书"。

### 2.2 开/不通的分界：为什么微信浏览器能通、Chrome 不通？

* 各自走**独立的 DNS 解析通道**
* 微信内置浏览器有自己的网络栈/DNS 策略，能拿到真实 IP
* Chrome 走系统 DNS → 被 OpenClash 劫持 → 拿不到 → 打不开
* 所以「部分能开部分不能」**强烈指向 DNS，而非证书/服务**

### 2.3 验证方法（关键实证工具）

* 证书：`openssl s_client -connect <ip>:443 -servername <域名>` 看 `Verify return code`
* DNS：`dig @<网关IP> <域名> A` 直查网关，绕过本地缓存
* 交叉对照：拿 `nexterm.onecloud.xin`（正常）对比 `vault.onecloud.xin`（异常）


---

## 三、解决方案

### 3.1 部署 Caddy 反代 + DNS-01 真证书（已完成，可复用）

**为什么不能直接 HTTP 访问 vaultwarden**：Vaultwarden 前端依赖 Subtle Crypto API，Chrome/Safari 只在安全上下文（HTTPS 或 localhost）开放，HTTP 直连必然报错。因此必须上反代 + TLS。

**为何选 DNS-01 而非 HTTP-01**：内网环境，Caddy 无公网 80/443 可达；DNS-01 通过 TXT 记录验证，无需公网端口，适合内网签发真证书。

**镜像选型**：官方 `caddy:latest` **不带 DNS challenge 插件**，需用 `caddy:2-builder` 多阶段构建加入 `caddy-dns/alidns`。

#### Caddyfile（`~/caddy/conf/Caddyfile`）

```
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

#### Dockerfile（`~/caddy/Dockerfile`）

```
FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/alidns

FROM caddy:2

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

#### docker-compose.yml 关键点

* `build: .` 构建本地镜像 `caddy-alidns`
* 注入环境变量（**注意命名**，这是 plugin 真正的变量名，别用错）：
  * `ALIYUN_ACCESS_KEY_ID`
  * `ALIYUN_ACCESS_KEY_SECRET`
* ⚠️ **最初用** `**ALICLOUD_ACCESS_KEY**` **报** `**AccessKeyID or AccessKeySecret is empty**` —— 因为插件底层走阿里云 SDK，用 `ALIYUN_ACCESS_KEY_ID/SECRET`，不是 lego 的 `ALICLOUD_*`。

#### DNS 记录

* `vault.onecloud.xin A → 192.168.31.1`（内网 IP）
* 权威侧用 DoH（`https://doh.pub/dns-query?name=...&type=A`）验证，绕过本机劫持

### 3.2 内网 DNS 解析问题（本次真正的终局根因）

**现象**：`dig @192.168.31.11 vault.onecloud.xin A` 返回 `NOERROR` 但 `ANSWER: 0`（空应答）

**根因（两层叠加）**：


1. **DNS 透明劫持**：OpenClash fake-ip 模式用 iptables 劫持所有 53 端口流量，即使指定公网 DNS 也会被接管（实测 `nslookup calibre.onecloud.xin 223.5.5.5` 也返回 fake-ip `198.18.x.x`）
2. **私有 IP 过滤**：Clash 默认过滤 DNS 响应中的私有 IP（防 DNS rebinding 攻击），`192.168.31.1` 是私有地址 → 被丢弃 → 空应答

**终极解决方案（推荐，最稳）**：让路由器本地 DNS（dnsmasq）直接解析内网域名，不经过 OpenClash。

在网关 OpenWrt 上：

```bash

echo "192.168.31.1 vault.onecloud.xin" >> /etc/hosts
/etc/init.d/dnsmasq restart
```

> ⚠️ 用逐条 hosts，不要用 `address=/onecloud.xin/192.168.31.1` 通配——否则会覆盖 `nexterm` 等本应走公网的子域。

> **原因**：内网域名解析应由本地 DNS 兜底，不应依赖公网 DNS 和代理工具（Clash 的私有 IP 过滤会拦截内网 A 记录）。


---

## 四、结论与可复用要点


1. **「部分浏览器能开部分不能」在 fake-ip 环境 ≈ DNS 问题，先查解析，别归咎证书**
2. 判断证书是否可信优先用 `openssl s_client` 的 `Verify return code`，原生可信链过 = 证书没问题
3. 内网域名 DNS 用 dnsmasq hosts 兜底，是最小改动、最可靠的做法
4. Caddy 插件变量名以插件 README 为准（安装后实测），勿照抄 lego 等上游库的命名

## 五、后续待办

- [ ] vaultwarden 启用 2FA
- [ ] `SIGNUPS_ALLOWED=false` 关闭开放注册