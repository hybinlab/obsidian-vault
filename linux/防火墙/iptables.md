---
tags:
  - linux
  - 防火墙
publish: true
---
上层命令，规则最终由 [[linux/防火墙/nftables.md|nftables]] 内核框架执行（`iptables -V` 输出含 `(nf_tables)` 即为兼容层，`(legacy)` 才是真正走旧代码路径）。总览见 [[防火墙总览]]。

## 五条链

|链|作用|使用频率|
|---|---|---|
|PREROUTING|路由决策前|NAT 场景|
|**INPUT**|入站到本机的流量|**最常用**|
|OUTPUT|本机发出的流量|较少手动管理|
|FORWARD|经本机转发的流量|网关/容器场景|
|POSTROUTING|路由决策后|NAT 场景|

## 四种动作

|动作|行为|场景|
|---|---|---|
|ACCEPT|允许通过|放行合法流量|
|DROP|直接丢弃，无回应|生产环境常用，更隐蔽|
|REJECT|拒绝并返回响应包|对方立刻知道被拒|
|LOG|仅记录日志|调试/审计|

> DROP vs REJECT：DROP 不暴露主机存在，REJECT 暴露但对方不用等超时。生产环境一般用 DROP。

## 匹配机制

- 规则**从上到下逐条匹配**，命中即执行，不再往下走
- 所有规则都不匹配 → 执行**默认策略**（ACCEPT 或 DROP）
- `-I` 插入到链首（优先级高），`-A` 追加到链尾

## 常用命令

```bash
# 查看规则（推荐加 -n 避免 DNS 解析慢，-v 显示计数）
iptables -nvL

# 添加规则
iptables -I INPUT -s 192.168.31.1 -p tcp --dport 22 -j REJECT   # 拒绝指定IP的SSH
iptables -I INPUT -s 192.168.10.0/24 -p tcp --dport 22 -j ACCEPT # 允许网段
iptables -A INPUT -p tcp --dport 1000:1024 -j REJECT             # 拒绝端口范围

# 删除规则
iptables -D INPUT 1        # 删除第1条
iptables -F                # 清空所有规则

# 修改默认策略
iptables -P INPUT ACCEPT
```

## 规则持久化

iptables 规则默认只在**当前运行时**生效，重启即丢，必须显式保存：

```bash
# CentOS/RHEL 7+，需先安装 iptables-services
iptables-save > /etc/sysconfig/iptables    # 手动导出当前规则到文件
service iptables save                       # 效果等价，输出 [ OK ] 才算保存成功

# 恢复规则
iptables-restore < /etc/sysconfig/iptables
```

> `iptables-save`/`iptables-restore` 是通用命令；`service iptables save` 是 CentOS 6/7 上 `iptables-services` 包提供的封装，本质还是调用前者写入 `/etc/sysconfig/iptables`。

## 关键参数

| 参数                      | 含义        | 示例                                                 |
| ----------------------- | --------- | -------------------------------------------------- |
| `-s`                    | 源地址       | `-s 192.168.1.0/24`                                |
| `-d`                    | 目标地址      | `-d 10.0.0.1`                                      |
| `-p`                    | 协议        | `-p tcp` / `-p udp` / `-p icmp`                    |
| `--dport`               | 目标端口      | `--dport 22` / `--dport 1000:1024`                 |
| `--sport`               | 源端口       | `--sport 8080`                                     |
| `-i` / `-o`             | 入/出网卡     | `-i eth0`                                          |
| `!`                     | 取反        | `-s ! 192.168.1.1`（非该IP）                           |
| `-m multiport --dports` | 匹配多个不连续端口 | `-m multiport --dports 22,80,443`                  |
| `-m state --state`      | 连接状态匹配    | `-m state --state ESTABLISHED,RELATED`（放行已建立连接的回包） |
| `-j`                    | 动作        | `-j ACCEPT` / `-j DROP` / `-j REJECT`              |
| `-I`                    | 插入到链首     | `-I INPUT`                                         |
| `-A`                    | 追加到链尾     | `-A INPUT`                                         |
| `-N` / `-X`             | 新建/删除自定义链 | `-N LOGDROP`                                       |

> `-m state --state ESTABLISHED,RELATED -j ACCEPT` 几乎是所有 INPUT 链的第一条规则，否则出站请求的回包会被拦。
