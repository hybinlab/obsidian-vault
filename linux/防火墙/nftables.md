---
tags:
  - linux
  - 防火墙
publish: true
---
	[[linux/防火墙/iptables.md|iptables]]/ip6tables/arptables/ebtables 的统一替代品，2026 年主流发行版的**实际执行者**（iptables 命令只是翻译层，走它的人本质还是在配置 nftables）。总览见 [[防火墙总览]]。

## 核心概念

| 概念     | 说明                                                                  |
| ------ | ------------------------------------------------------------------- |
| family | `ip`(v4) / `ip6`(v6) / `inet`(v4+v6合一，推荐) / `arp` / `bridge`        |
| table  | 规则的容器，自己建、自己命名，如 `inet filter`                                      |
| chain  | 挂在 table 下，需手动声明 hook（`input`/`forward`/`output`）和优先级才会生效，否则只是普通容器链 |
| set    | 可复用的地址/端口集合，替代 iptables 里重复写多条规则                                    |

## 常用命令

```bash
# 查看
nft list ruleset                 # 查看全部规则（对应 iptables -nvL）
nft list tables

# 建表建链（inet 同时管 v4/v6）
nft add table inet filter
nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }

# 加规则
nft add rule inet filter input tcp dport 22 accept
nft add rule inet filter input ip saddr 192.168.10.0/24 tcp dport 22 accept
nft add rule inet filter input ct state established,related accept

# set 用法：一条规则放行多个端口，等价于 iptables 的 multiport
nft add rule inet filter input tcp dport { 22, 80, 443 } accept

# 删除/清空
nft delete rule inet filter input handle <handle号>   # 需先 nft -a list ruleset 看handle
nft flush ruleset                # 清空所有

# 持久化（发行版差异较大）
nft list ruleset > /etc/nftables.conf
systemctl enable --now nftables
```

> 判断当前内核后端：`iptables -V` 输出含 `(nf_tables)` 说明底层已经是 nftables 在跑，`(legacy)` 才是真正的旧 iptables。
