# Nmap

* 使用 IP 地址范围`-`：如果您想扫描 192.168.0.1 到 192.168.0.10 之间的所有 IP 地址，可以这样写：`192.168.0.1-10`
* 使用 IP 子网`/`：如果要扫描一个子网，可以将其表示为`192.168.0.1/24`，这等价于`192.168.0.0-255`
* 主机名：您也可以通过主机名指定目标，例如：`example.thm`


想发现网络上的在线主机。Nmap 提供了 -sn 选项

```sql
root@tryhackme:~# nmap -sn 192.168.66.0/24
Starting Nmap 7.92 ( https://nmap.org ) at 2024-08-07 13:49 EEST
Nmap scan report for XiaoQiang (192.168.66.1)
Host is up (0.0069s latency).
MAC Address: 44:DF:65:D8:FE:6C (Unknown)
Nmap scan report for S190023240007 (192.168.66.88)
Host is up (0.090s latency).
MAC Address: 7C:DF:A1:D3:8C:5C (Espressif)
Nmap scan report for wlan0 (192.168.66.97)
Host is up (0.20s latency).
MAC Address: 10:D5:61:E2:18:E6 (Tuya Smart)
Nmap scan report for 192.168.66.179
Host is up (0.10s latency).
MAC Address: E4:AA:EC:8F:88:C9 (Tianjin Hualai Technology)
[...]
Nmap done: 256 IP addresses (7 hosts up) scanned in 2.64 seconds
```



| `-sT` | __TCP__连接扫描——完成三次握手 |
|----|----|
| `-sS` | __TCP__ SYN——三次握手的第一步 |
| `-sU` | __UDP__扫描 |
| `-F` | 快速模式——扫描 100 个最常用的端口 |
| `-p[range]` | 指定端口号范围——`-p-`扫描所有端口 |
| `-O` | __操作系统__检测 |
| `-sV` | 服务和版本检测 |
| `-A` | __操作系统__检测、版本检测及其他新增功能 |
| `-Pn` | 扫描看似已关闭的主机 |

# TCP扫描

`-sT`参数进行TCP的扫描

使用`-Ss`参数进行SYN扫描（半扫），不会进行TCP三次握手，因此更隐蔽


# UDP扫描

`-sU`进行__UDP__扫描


# 版本扫描

`-O`参数进行操作系统的检测


# 服务检测

`-sV`进行目标服务器的服务扫描


# 输出报告

`-v`选项足以提供详细的输出；但是，如果您仍然不满意，可以通过添加另一个"v"来提高详细程度，例如"+"`-vv`或"- " `-vvvv`。您也可以直接指定详细程度，例如" +"`-v2`和`-v4`"-"。甚至可以在扫描开始后按"v"来提高详细程度。


__在__许多情况下，我们需要保存扫描结果。Nmap提供多种格式。根据命令的不同，其中最常用的三种格式是：普通（易于阅读）输出、__XML__输出和可 grep 的输出。您可以按如下方式选择扫描报告格式：`grep`

* `-oN <filename>`- 正常输出
* `-oX <filename>`- __XML__输出
* `-oG <filename>`-可输出（对and`grep`有用）`grepawk`
* `-oA <basename>`- 输出所有主要格式

```sql
root@tryhackme:~# nmap -sS 192.168.139.1 -oA gateway
Starting Nmap 7.92 ( https://nmap.org ) at 2024-08-13 19:35 EEST
Nmap scan report for g5000 (192.168.139.1)
Host is up (0.0000070s latency).
Not shown: 999 closed tcp ports (reset)
PORT    STATE SERVICE
902/tcp open  iss-realsecure

Nmap done: 1 IP address (1 host up) scanned in 0.13 seconds
# ls
gateway.gnmap  gateway.nmap  gateway.xml #输出所有格式的报告
```


# 总结

| **选项** | **解释** |
|----|----|
| `-sL` | 列表扫描 – 列出目标而无需扫描 |
| ***主机发现*** |    |
| `-sn` | Ping 扫描 – 仅主机发现 |
| ***端口扫描*** |    |
| `-sT` | __TCP__连接扫描——完成三次握手 |
| `-sS` | __TCP__ SYN——三次握手的第一步 |
| `-sU` | __UDP__扫描 |
| `-F` | 快速模式——扫描 100 个最常用的端口 |
| `-p[range]` | 指定端口号范围——`-p-`扫描所有端口 |
| `-Pn` | 将所有主机视为在线——扫描看似已关闭的主机 |
| ***服务检测*** |    |
| `-O` | __操作系统__检测 |
| `-sV` | 服务版本检测 |
| `-A` | __操作系统__检测、版本检测及其他新增功能 |
| ***定时*** |    |
| `-T<0-5>` | 时间模板——多疑（0）、鬼鬼祟祟（1）、礼貌（2）、正常（3）、好斗（4）、疯狂（5） |
| `--min-parallelism <numprobes>`和`--max-parallelism <numprobes>` | 并行探针的最小和最大数量 |
| `--min-rate <number>`和`--max-rate <number>` | 最小和最大速率（数据包/秒） |
| `--host-timeout` | 等待目标主机的最长时间 |
| ***实时输出*** |    |
| `-v` | 冗长程度——例如，`-vv`以及`-v4` |
| `-d` | 调试级别——例如`-d`和`-d9` |
| ***报告*** |    |
| `-oN <filename>` | 正常输出 |
| `-oX <filename>` | __XML__输出 |
| `-oG <filename>` | `grep`可输出 |
| `-oA <basename>` | 输出格式均为所有主流格式 |