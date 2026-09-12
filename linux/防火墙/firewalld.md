---
tags:
  - linux
  - 防火墙
publish: true
---
RHEL/CentOS 系。对 [[linux/防火墙/nftables.md|nftables]]/[[linux/防火墙/iptables.md|iptables]] 的**动态管理层**，核心概念是 **zone（区域）**：把网卡分配到不同 zone，每个 zone 预设安全策略，改规则不用整体 reload 内核规则表。总览见 [[防火墙总览]]。

## Zone

|Zone|默认规则策略|
|---|---|
|trusted|允许所有的数据包|
|home|拒绝流入的流量，除非与流出的流量相关；如果流量与 ssh、mdns、ipp-client、samba-client 与 dhcpv6-client 服务相关，则允许流量|
|internal|等同于 home 区域|
|work|拒绝流入的流量，除非与流出的流量相关；如果流量与 ssh、ipp-client 与 dhcpv6-client 服务相关，则允许流量|
|public（默认）|拒绝流入的流量，除非与流出的流量相关；如果流量与 ssh、dhcpv6-client 服务相关，则允许流量|
|external|拒绝流入的流量，除非与流出的流量相关；如果流量与 ssh 服务相关，则允许流量|
|dmz|拒绝流入的流量，除非与流出的流量相关；如果流量与 ssh 服务相关，则允许流量|
|block|拒绝流入的流量，除非与流出的流量相关|
|drop|拒绝流入的流量，除非与流出的流量相关，且不产生任何回应|

## Runtime 与 Permanent 两种模式

- **Runtime（运行时）**：默认模式，命令不加 `--permanent` 即为此模式，当前立即生效，**重启后失效**
- **Permanent（永久）**：命令加 `--permanent`，写入配置文件可永久保存，但**不立即生效**，只在系统重启后自动生效；若想立即生效需手动执行 `firewall-cmd --reload`

> 生产环境常见做法：先不加 `--permanent` 测试规则是否符合预期，确认无误后再加 `--permanent` 固化，最后 `--reload` 让两边状态一致。

## 常用命令与参数

```bash
firewall-cmd --get-default-zone               # 查看默认zone
firewall-cmd --set-default-zone=public         # 设置默认zone，永久生效
firewall-cmd --get-zones                        # 显示可用的区域
firewall-cmd --get-services                      # 显示预先定义的服务
firewall-cmd --get-active-zones                 # 查看当前正在使用的区域与网卡名称
firewall-cmd --list-all                          # 查看当前zone完整规则（网卡/资源/端口/服务等）
firewall-cmd --list-all-zones                     # 查看所有zone的完整规则
firewall-cmd --list-all --zone=public             # 指定zone

firewall-cmd --add-service=http --permanent       # 设置默认zone允许该服务的流量
firewall-cmd --remove-service=http --permanent    # 设置默认zone不再允许该服务的流量
firewall-cmd --add-port=8080/tcp --permanent      # 设置默认zone允许该端口的流量
firewall-cmd --add-port=6000-6010/udp --permanent # 端口范围
firewall-cmd --remove-port=8080/tcp --permanent   # 设置默认zone不再允许该端口的流量

firewall-cmd --add-source=192.168.1.0/24 --zone=trusted --permanent    # 将来自该IP/子网的流量导向指定区域
firewall-cmd --remove-source=192.168.1.0/24 --zone=trusted --permanent # 不再导向该区域
firewall-cmd --add-interface=eth1 --zone=internal --permanent          # 将该网卡的所有流量导向指定区域
firewall-cmd --change-interface=eth0 --zone=public --permanent         # 将某个网卡与区域重新关联

firewall-cmd --reload                             # 让“永久生效”的配置规则立即生效，并覆盖当前的配置规则
firewall-cmd --panic-on                            # 开启应急状况模式：立即切断所有网络连接（含已建立的）
firewall-cmd --panic-off                           # 关闭应急状况模式
```

|参数|含义|
|---|---|
|`--permanent`|写入配置文件，不立即生效，需配合 `--reload`|
|（不加）|Runtime 模式，立即生效，重启后失效|
|`--zone=`|指定作用的 zone，不写则用默认 zone|
|`--add-service=` / `--remove-service=`|按预置服务名放行/取消（`--get-services` 看全部）|
|`--add-port=` / `--remove-port=`|按 `端口/协议` 放行/取消|
|`--add-source=` / `--remove-source=`|按来源 IP/子网 导向/取消导向某 zone|
|`--add-interface=` / `--change-interface=`|把网卡加入某 zone / 把网卡改关联到某 zone|
|`--panic-on` / `--panic-off`|应急模式开关，出现攻击时一键断网|

> ⚠️ `--permanent` 和不加是两套独立状态，改配置永远要加 `--permanent` 再 `--reload`，否则重启就丢。
