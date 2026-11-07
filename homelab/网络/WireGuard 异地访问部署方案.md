---
publish: false
tags:
  - homelab
  - WireGuard
  - VPN
---

# WireGuard 异地访问与家庭代理部署 SOP

## 目标与网络规划

手机在外仅开启 WireGuard，即可访问家庭 VM，并经家庭 OpenWrt/OpenClash 按规则上网。家庭端 WireGuard 部署在 bastion，OpenWrt 沿用现有网关、DNS 和代理配置。

```text
手机 / Mac
   │ WireGuard，公网 UDP 51820
   ▼
阿里云 ECS
   │ WireGuard
   ▼
bastion
   ├── 家庭同网段 VM：直接转发
   └── 上网流量：OpenWrt → 家庭上级网关 → 直连或代理节点
```

| 节点 | 地址 / 接口 | 角色 |
| --- | --- | --- |
| ECS | wg0：10.77.0.1/24；fd77:77:77::1/64；出口 eth0 | 公网接入、中转 |
| bastion | wg0：10.77.0.2/24；ens18：192.168.31.3/24 | 家庭转发与 NAT |
| OpenWrt | LAN：192.168.31.11；WAN：192.168.1.2 | 默认网关、DNS、OpenClash |
| 家庭上级网关 | 192.168.1.1 | 家庭公网出口 |
| 手机 | 10.77.0.11/32；fd77:77:77::11/128 | 全流量客户端 |
| Mac | 10.77.0.10/32 | 可选客户端，独立密钥 |

本文所有密钥字段均为占位符，不保存真实私钥或公钥。`<ECS_PUBLIC_IP>` 使用实际 ECS 公网地址。网卡名和网段按实际环境核对。

本方案提供 IPv4 上网；IPv6 在手机侧纳入隧道、在 ECS 侧拒绝，暂不提供 IPv6 出口。服务端设置不能代替手机实际验收。

## 1. 部署前检查

在 ECS 和 bastion 上以 root 执行：

```bash
cat /etc/os-release
ip -br address
ip route
ip rule
ss -lunp
sysctl net.ipv4.ip_forward
iptables-save
ip6tables-save
systemctl is-active wg-quick@wg0
```

确认：

- VPN 网段与家庭 LAN、云 VPC、Docker、其他 VPN 无冲突。
- bastion 默认路由经 `192.168.31.11`，ECS 沿用自己的云网关。
- UDP 51820 未被其他服务占用，路由表 177、策略优先级 17710/17711 未被使用。
- 不覆盖已有 `wg0.conf`，不清空 Docker、FRP 或其他防火墙规则。
- ECS 安全组入方向允许 UDP 51820。移动网络来源地址不固定时，来源可设为 `0.0.0.0/0`；隧道内访问仍须通过密钥认证。

备份现有规则与路由，备份不包含 WireGuard 密钥：

```bash
install -d -m 700 /etc/wireguard
snapshot_dir="/etc/wireguard/pre-home-$(date +%Y%m%d-%H%M%S)"
install -d -m 700 "$snapshot_dir"
iptables-save > "$snapshot_dir/iptables"
ip6tables-save > "$snapshot_dir/ip6tables"
ip route show table all > "$snapshot_dir/routes"
ip rule > "$snapshot_dir/rules"
```

快照用于核对，不直接向仍运行 Docker 的系统恢复过时的完整规则集。

## 2. 安装与生成密钥

Ubuntu/Debian 两端分别执行：

```bash
apt-get update
apt-get install -y --no-install-recommends wireguard-tools
install -d -m 700 /etc/wireguard
```

每台服务器在本机生成独立密钥；已有文件时先确认用途，不覆盖：

```bash
cd /etc/wireguard
umask 077
wg genkey > server.key
wg pubkey < server.key > server.pub
```

部署时通过可信渠道交换公钥；私钥留在所属设备，不复制进文档、Git 或聊天。手机在 WireGuard App 内生成自己的密钥，不复用服务器私钥。

## 3. 配置两端 WireGuard

配置文件统一为 `/etc/wireguard/wg0.conf`，权限 `600`。在服务器本地将占位符替换成相应值。

### ECS

```ini
[Interface]
Address = 10.77.0.1/24, fd77:77:77::1/64
PrivateKey = <ECS_PRIVATE_KEY>
ListenPort = 51820
MTU = 1380
Table = off

[Peer]
# 家庭 bastion
PublicKey = <BASTION_PUBLIC_KEY>
AllowedIPs = 0.0.0.0/0

[Peer]
# 手机
PublicKey = <PHONE_PUBLIC_KEY>
AllowedIPs = 10.77.0.11/32, fd77:77:77::11/128
```

Mac 接入时另加一个 Peer，公钥使用 `<MAC_PUBLIC_KEY>`，AllowedIPs 为 `10.77.0.10/32`；未接入时不添加该 Peer。

`Table = off` 禁止 wg-quick 自动建立默认路由。bastion 的 `0.0.0.0/0` 用于 WireGuard 内部选路和接收公网来源回包，不直接改变 ECS 自身的默认出口。手机/Mac 更具体的 `/32` Peer 用于选择回包接收端。

### bastion

```ini
[Interface]
Address = 10.77.0.2/24
PrivateKey = <BASTION_PRIVATE_KEY>
MTU = 1380
Table = off
PostUp = /bin/sh /etc/wireguard/home-routing up
PreDown = /bin/sh /etc/wireguard/home-routing down

[Peer]
PublicKey = <ECS_PUBLIC_KEY>
Endpoint = <ECS_PUBLIC_IP>:51820
AllowedIPs = 10.77.0.1/32, 10.77.0.10/32, 10.77.0.11/32
PersistentKeepalive = 25
```

bastion 主动连接 ECS，无需家庭公网 IPv4 或入站端口映射。不要在 bastion 的该 Peer 中添加 IPv4 默认路由，否则可能使隧道外层流量回灌隧道。

两端执行：

```bash
chmod 600 /etc/wireguard/wg0.conf
```

## 4. 开启转发与添加规则脚本

两端写入 `/etc/sysctl.d/70-wireguard-home.conf`：

```ini
net.ipv4.ip_forward = 1
```

应用：

```bash
sysctl -p /etc/sysctl.d/70-wireguard-home.conf
```

两端创建 `/etc/wireguard/home-routing`，使用以下脚本。ECS 保留 `ROLE=ecs`；bastion 改成 `ROLE=bastion`。脚本仅管理本方案的专用链与策略，不修改全局默认策略。

```sh
#!/bin/sh
set -eu
ROLE=ecs
CLIENTS="10.77.0.10/32 10.77.0.11/32"

case "${1:-}" in
up)
    iptables -w 5 -N WG_HOME_FWD
    iptables -w 5 -A WG_HOME_FWD -m conntrack --ctstate INVALID -j DROP
    iptables -w 5 -A WG_HOME_FWD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    if [ "$ROLE" = ecs ]; then
        out_if=wg0
    else
        out_if=ens18
    fi
    for src in $CLIENTS; do
        iptables -w 5 -A WG_HOME_FWD -i wg0 -o "$out_if" -s "$src" -j ACCEPT
    done
    iptables -w 5 -A WG_HOME_FWD -j REJECT --reject-with icmp-admin-prohibited
    iptables -w 5 -I FORWARD 1 -i wg0 -j WG_HOME_FWD
    iptables -w 5 -I FORWARD 1 -o wg0 -j WG_HOME_FWD

    iptables -w 5 -N WG_HOME_IN
    iptables -w 5 -A WG_HOME_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    iptables -w 5 -A WG_HOME_IN -p icmp -j ACCEPT
    if [ "$ROLE" = bastion ]; then
        for src in $CLIENTS; do
            iptables -w 5 -A WG_HOME_IN -s "$src" -p tcp --dport 22 -j ACCEPT
        done
    fi
    iptables -w 5 -A WG_HOME_IN -j REJECT --reject-with icmp-admin-prohibited
    iptables -w 5 -I INPUT 1 -i wg0 -j WG_HOME_IN

    if [ "$ROLE" = ecs ]; then
        iptables -w 5 -I INPUT 1 -i eth0 -p udp --dport 51820 -m comment --comment wg-home-listen -j ACCEPT
        ip6tables -w 5 -N WG_HOME_V6
        ip6tables -w 5 -A WG_HOME_V6 -j REJECT --reject-with icmp6-adm-prohibited
        ip6tables -w 5 -I INPUT 1 -i wg0 -j WG_HOME_V6
        ip6tables -w 5 -I FORWARD 1 -i wg0 -j WG_HOME_V6
        ip route add default dev wg0 table 177
        ip rule add priority 17710 from 10.77.0.10/32 lookup 177
        ip rule add priority 17711 from 10.77.0.11/32 lookup 177
    else
        iptables -w 5 -t nat -N WG_HOME_NAT
        for src in $CLIENTS; do
            iptables -w 5 -t nat -A WG_HOME_NAT -s "$src" -o ens18 -j MASQUERADE
        done
        iptables -w 5 -t nat -I POSTROUTING 1 -j WG_HOME_NAT
        sysctl -q -w net.ipv4.conf.wg0.rp_filter=0
    fi
    ;;
down)
    if [ "$ROLE" = ecs ]; then
        ip rule del priority 17710 from 10.77.0.10/32 lookup 177 2>/dev/null || true
        ip rule del priority 17711 from 10.77.0.11/32 lookup 177 2>/dev/null || true
        ip route del default dev wg0 table 177 2>/dev/null || true
        iptables -w 5 -D INPUT -i eth0 -p udp --dport 51820 -m comment --comment wg-home-listen -j ACCEPT 2>/dev/null || true
        ip6tables -w 5 -D INPUT -i wg0 -j WG_HOME_V6 2>/dev/null || true
        ip6tables -w 5 -D FORWARD -i wg0 -j WG_HOME_V6 2>/dev/null || true
        ip6tables -w 5 -F WG_HOME_V6 2>/dev/null || true
        ip6tables -w 5 -X WG_HOME_V6 2>/dev/null || true
    else
        iptables -w 5 -t nat -D POSTROUTING -j WG_HOME_NAT 2>/dev/null || true
        iptables -w 5 -t nat -F WG_HOME_NAT 2>/dev/null || true
        iptables -w 5 -t nat -X WG_HOME_NAT 2>/dev/null || true
    fi
    iptables -w 5 -D INPUT -i wg0 -j WG_HOME_IN 2>/dev/null || true
    iptables -w 5 -D FORWARD -i wg0 -j WG_HOME_FWD 2>/dev/null || true
    iptables -w 5 -D FORWARD -o wg0 -j WG_HOME_FWD 2>/dev/null || true
    for chain in WG_HOME_IN WG_HOME_FWD; do
        iptables -w 5 -F "$chain" 2>/dev/null || true
        iptables -w 5 -X "$chain" 2>/dev/null || true
    done
    ;;
*) exit 2 ;;
esac
```

设置权限并检查语法：

```bash
chmod 700 /etc/wireguard/home-routing
sh -n /etc/wireguard/home-routing
```

规则含义：

| 位置 | 处理 |
| --- | --- |
| ECS 策略路由 | 仅手机/Mac 来源查表 177，从 wg0 发往家庭端；ECS 自身保留原出口 |
| ECS WG_HOME_FWD | 授权客户端 wg0 → wg0 转发，并允许相关回包 |
| ECS WG_HOME_IN | VPN 仅能访问 ECS 本机 ICMP及相关回包 |
| ECS WG_HOME_V6 | 拒绝隧道内 IPv6，本阶段不提供 IPv6 上网 |
| bastion WG_HOME_FWD | 授权客户端 wg0 → ens18 转发，并允许相关回包 |
| bastion WG_HOME_NAT | 将客户端来源转换为 bastion LAN 地址，解决家庭回程 |
| bastion WG_HOME_IN | 允许客户端访问 bastion 本机 SSH、ICMP及相关回包 |

`up` 不是可重复执行的命令；已有规则时不要手动再次调用。若启动部分失败，先停止服务，按 `down` 清理本方案残留，排除原因后再启动。

## 5. 配置服务与开机启动

### ECS：独立路由服务

ECS 使用独立 systemd 服务管理规则，避免依赖 wg-quick 执行自定义钩子。若 AppArmor 拒绝钩子执行，不关闭或放宽 AppArmor，使用以下服务结构。

创建 `/etc/systemd/system/wg-home-routing.service`：

```ini
[Unit]
Description=Home VPN policy routing and firewall
Requires=wg-quick@wg0.service
After=wg-quick@wg0.service
BindsTo=wg-quick@wg0.service
PartOf=wg-quick@wg0.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh /etc/wireguard/home-routing up
ExecStop=/bin/sh /etc/wireguard/home-routing down
```

创建 `/etc/systemd/system/wg-quick@wg0.service.d/home-routing.conf`，先建立对应目录：

```ini
[Unit]
Wants=wg-home-routing.service
```

启动：

```bash
systemctl daemon-reload
systemctl start wg-quick@wg0
systemctl is-active wg-quick@wg0 wg-home-routing
```

### bastion：接口钩子

bastion 的配置已通过 PostUp / PreDown 调用规则脚本：

```bash
systemctl start wg-quick@wg0
systemctl is-active wg-quick@wg0
```

确认双向握手和业务验证通过后，在两端启用开机启动：

```bash
systemctl enable wg-quick@wg0
```

ECS 的规则服务由 wg-quick 自动拉起，不需要单独 enable。

## 6. 手机接入

在官方 WireGuard App 创建空隧道，手机生成自己的密钥。将手机公钥登记到 ECS 的对应 Peer；手机私钥不离开手机。

```ini
[Interface]
PrivateKey = <PHONE_PRIVATE_KEY>
Address = 10.77.0.11/32, fd77:77:77::11/128
DNS = 192.168.31.11
MTU = 1380

[Peer]
PublicKey = <ECS_PUBLIC_KEY>
Endpoint = <ECS_PUBLIC_IP>:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
```

| 手机字段 | 填写内容 |
| --- | --- |
| 接口公钥 | 手机自己的公钥，提供给 ECS 登记 |
| 接口私钥 | App 生成并在手机保管，不填写其他设备的私钥 |
| 接口地址 | 上面 Interface 的 Address |
| 对端公钥 | ECS 的公钥 |
| 对端 / Endpoint | ECS 公网地址和 UDP 端口 |
| 路由的 IP 地址（段） | `0.0.0.0/0, ::/0` |
| 预共享密钥 | 本方案未配置，留空 |
| 手机监听端口 | 留空或自动，不必填写 51820 |

手机不需要同时开启 Clash。OpenClash 在家庭 OpenWrt 上运行。手机断开 WireGuard 后恢复原网络；本方案不提供永久断网保护。

## 7. 验收

手机关闭 Wi-Fi，使用蜂窝数据开启 WireGuard。按顺序验证：

1. ECS 的手机 Peer 出现近期 `latest handshake`，具有双向 transfer。
2. ECS 与 bastion 的 Peer 同样存在近期握手和 Endpoint。
3. 手机打开 `https://192.168.31.2:8006`，或连接家庭 VM 的 SSH。
4. 手机打开普通网站和 Google，确认家庭代理规则生效。
5. 核对 DNS、实际出口及 IPv6 行为；配置了 IPv6 默认路由不等于已验证无旁路。
6. 重启 WireGuard 服务后复测；安排维护窗口再验证整机重启。

服务器检查命令：

```bash
wg show wg0
iptables -nvL WG_HOME_FWD
iptables -nvL WG_HOME_IN
```

ECS 额外检查：

```bash
systemctl is-active wg-home-routing
ip rule
ip route show table 177
ip route get 1.1.1.1 from 10.77.0.11 iif wg0
ip6tables -nvL WG_HOME_V6
```

bastion 额外检查：

```bash
iptables -t nat -nvL WG_HOME_NAT
ip route get 1.1.1.1
ip route get 10.77.0.11
```

验收标准是手机实际内网访问与代理上网正常，不以“隧道开关开启”或“发送计数增加”作为成功依据。

## 8. 排障

| 现象 | 检查与处理 |
| --- | --- |
| ECS 收不到手机握手包 | 核对 Endpoint、手机网络、UDP 51820 安全组及主机防火墙 |
| 握手包到达但无成功握手 | 核对双方公钥、是否对应当前私钥、是否误填预共享密钥；注意 I / l / L，避免手工转录 |
| 手机握手成功，网页与内网都不通 | 同时检查家庭端 Peer，不能只检查手机 Peer；再查表 177 和 FORWARD |
| ECS 家庭 Peer 暂无 Endpoint，bastion 仍显示旧会话 | 从 bastion 发包触发重新握手；必要时重启 bastion 的 wg-quick@wg0 后复核 |
| bastion 已收到手机包但没有回包 | 检查 SNAT、家庭默认网关、目标服务和家庭防火墙 |
| 内网 IP 可访问，域名或外网失败 | 检查 DNS 192.168.31.11、OpenClash 接管与规则 |
| wg-quick 因脚本执行权限失败 | 检查服务日志和 AppArmor；ECS 采用独立路由服务，不关闭安全机制 |
| 软件源下载失败，解析到 198.18.x.x | 检查代理路径；可选其他可信官方镜像，不为安装 VPN 随意改动家庭代理 |

日志与连通检查：

```bash
journalctl -u wg-quick@wg0 -n 100 --no-pager
# ECS 上额外执行
journalctl -u wg-home-routing -n 100 --no-pager
# bastion 上执行
ping -c 3 -W 2 10.77.0.1
```

需要抓包时只检查必要包头，不导出含私钥的配置或业务载荷。日志和排障材料进入文档前也需去掉真实密钥。

## 9. 维护、轮换与回退

查看状态或重启：

```bash
systemctl status wg-quick@wg0 --no-pager
systemctl restart wg-quick@wg0
```

修改 `wg0.conf` 后需重新加载或重启才会生效；仅修改文件不会改变运行配置。管理端使用 `wg set` 时，同时维护配置文件，保证重启后不丢失。手机修改后保存并关闭、再开启隧道。

密钥泄漏时，在所属设备生成新密钥，同步更新其运行配置、持久化配置及所有对端保存的公钥，撤销旧 Peer，再验证握手与业务。密钥值不写入 SOP。

停止并取消开机启动：

```bash
systemctl disable --now wg-quick@wg0
```

正常停止会删除本方案的专用链与策略路由；ECS 的规则服务随之停止。异常残留时，在服务已停止且不存在其他同名链用途的前提下，使用规则脚本清理：

```bash
/bin/sh /etc/wireguard/home-routing down
```

不要直接关闭全局 IP 转发，也不要清空防火墙，以免影响 Docker 等已有业务。

## 成本与安全边界

手机上网消耗蜂窝流量、ECS 公网流量或带宽以及家庭宽带。OpenClash 按规则决定直连或代理，不保证所有网站都使用代理节点。

ECS 是两段 WireGuard 隧道的解密和再加密节点，可以看到内层 IP 数据包。SSH、HTTPS 有应用层加密；普通 HTTP 没有。ECS、bastion、OpenWrt 均为可信节点。bastion 到其他家庭 VM 的直连链路不受这两段 WireGuard 隧道保护。

## 官方参考

- [WireGuard Quick Start](https://www.wireguard.com/quickstart/)
- [wg-quick 官方手册](https://git.zx2c4.com/wireguard-tools/about/src/man/wg-quick.8)
- [Ubuntu：转发与 NAT](https://ubuntu.com/server/docs/how-to/wireguard-vpn/vpn-as-the-default-gateway/)
