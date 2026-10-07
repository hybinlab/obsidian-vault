
---
tags:
  - VPN
  - 排障
---
## 环境

* 路由器：OpenWrt + OpenClash（Meta 内核）
* DNS 模式：fake-ip
* 域名：onecloud.xin（阿里云 DNS 托管）
* 内网网段：192.168.31.0/24
* 路由器 IP：192.168.31.11

## 问题现象

Mac 终端执行 `nslookup vault.onecloud.xin` 返回 `No answer`，无法解析域名。

阿里云 DNS 控制台已正确配置 A 记录：`vault.onecloud.xin → 192.168.31.1`，且手机 4G 网络下可正常访问。

## 排查过程

### 1. 确认是否为域名记录问题

指定公网 DNS 直接查询：

```bash

nslookup vault.onecloud.xin 223.5.5.5
```

结果仍然 `No answer`，初步怀疑 DNS 记录未生效。

### 2. 交叉验证其他子域名

```bash

nslookup calibre.onecloud.xin 223.5.5.5
```

返回 `198.18.5.247`（fake-ip 地址段），说明即使指定了 223.5.5.5，DNS 查询仍被 OpenClash 透明劫持（iptables 重定向 53 端口），实际并未到达公网 DNS。

### 3. 定位根因

问题由两层因素叠加导致：

* **DNS 劫持**：OpenClash 在 fake-ip 模式下通过 iptables 劫持所有 53 端口流量，客户端无论指定什么 DNS 服务器，查询都会被 Clash 接管。
* **私有 IP 过滤**：Clash 默认过滤 DNS 响应中的私有 IP 地址（防 DNS rebinding 攻击），`192.168.31.1` 属于私有地址段，响应被丢弃，导致返回 `No answer`。

## 解决方案

### 方案一：dnsmasq 本地解析（推荐）

在 OpenWrt 的 `/etc/hosts` 中添加内网域名映射，让 dnsmasq 直接返回结果，请求不经过 OpenClash。

**单条添加：**

```bash

echo "192.168.31.1 vault.onecloud.xin" >> /etc/hosts
/etc/init.d/dnsmasq restart
```

**批量添加：**

```bash

cat >> /etc/hosts << 'EOF'
192.168.31.1 vault.onecloud.xin

192.168.31.1 service2.onecloud.xin

192.168.31.1 service3.onecloud.xin

EOF
/etc/init.d/dnsmasq restart
```

**通配符（所有子域名指向同一 IP 时）：**

```bash

echo "address=/onecloud.xin/192.168.31.1" >> /etc/dnsmasq.conf
/etc/init.d/dnsmasq restart
```

> 注意：通配符会覆盖所有子域名。如果部分子域名需要解析到公网 IP，不能用通配符，需逐条写 hosts。

### 方案二：OpenClash 内处理（不推荐）

需要同时修改三处配置：


1. **fake-ip filter**：将域名加入 filter 列表，使 Clash 返回真实 IP 而非 fake-ip。
2. **规则设置**：添加 `DOMAIN-SUFFIX,onecloud.xin,DIRECT` 规则，确保流量直连。
3. **关闭私有 IP 过滤**：否则 `192.168.31.1` 仍会被 Clash 丢弃。

改动多，容易遗漏，且影响 Clash 全局安全策略，不建议使用。

## 结论

内网域名解析应由路由器本地 DNS（dnsmasq）处理，不应依赖公网 DNS 和代理工具。方案一改动最小、最可靠，且不影响 OpenClash 的其他配置。