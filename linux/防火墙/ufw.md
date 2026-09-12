---
tags:
  - linux
  - 防火墙
publish: true
---
Debian/Ubuntu 系。对 [[linux/防火墙/iptables.md|iptables]]/[[linux/防火墙/nftables.md|nftables]] 的**简化命令行封装**，语法比 [[linux/防火墙/firewalld.md|firewalld]] 更直白，没有 zone 概念，就是一条条 allow/deny 规则 + 应用 profile。总览见 [[防火墙总览]]。

## 常用命令与参数

```bash
ufw status verbose               # 查看状态和规则（一定加verbose，否则看不到细节）
ufw enable / disable             # 启用/禁用（enable会顺带设置开机自启）

ufw default deny incoming        # 默认策略：拒绝入站
ufw default allow outgoing       # 默认策略：允许出站

ufw allow 22/tcp                 # 放行端口+协议
ufw allow ssh                    # 用服务名（读 /etc/services）
ufw allow from 192.168.1.0/24                    # 放行某网段所有流量
ufw allow from 192.168.1.10 to any port 22 proto tcp  # 精确到 源IP+端口+协议
ufw deny 8080/tcp
ufw limit ssh                    # 限速：同一IP短时间内多次连接自动临时封禁（防爆破）

ufw delete allow 22/tcp          # 按规则内容删除
ufw status numbered               # 带编号查看，方便按编号删
ufw delete 3                      # 按编号删除

ufw app list                      # 查看已注册的应用profile（如 'Nginx Full'）
ufw allow 'Nginx Full'
```

|参数|含义|
|---|---|
|`allow` / `deny` / `reject`|放行 / 静默丢弃 / 拒绝并回应|
|`from`|限定源地址|
|`to any port`|限定目标端口|
|`proto`|限定协议 `tcp`/`udp`|
|`limit`|对高频连接自动限速封禁，SSH 端口强烈建议用它替代 allow|

> ufw 规则最终也是写入 iptables/nftables，`ufw status` 之外想看底层实际规则可以 `iptables -nvL` 或 `nft list ruleset` 交叉验证。
