---
publish: true
tags:
  - 渗透测试
  - 信息收集
---
查看更多命令使用`man tcpdump`

| **命令** | **解释** |
|----|----|
| `tcpdump -q` | 快捷安静：简明信息包 |
| `tcpdump -e` | 包括 MAC 地址 |
| `tcpdump -A` | 以 ASCII 编码打印数据包 |
| `tcpdump -xx` | 以十六进制格式显示数据包 |
| `tcpdump -X` | 以十六进制和 ASCII 格式显示数据包 |

| **命令** | **解释** |
|----|----|
| `tcpdump -i INTERFACE` | 捕获特定网络接口上的数据包 |
| `tcpdump -w FILE` | 将捕获的数据包写入文件 |
| `tcpdump -r FILE` | 从文件中读取捕获的数据包 |
| `tcpdump -c COUNT` | 捕获特定数量的数据包 |
| `tcpdump -n` | 不要解析 IP 地址 |
| `tcpdump -nn` | 不要解析 IP 地址，也不要解析协议号 |
| `tcpdump -v` | `-vv`详细显示；可以通过以下方式增加详细程度： |


示例：

* `tcpdump -i eth0 -c 50 -v`通过监听有线`eth0`以太网接口，捕获并显示 50 个数据包，并以详细方式显示它们。
* `tcpdump -i wlo1 -w data.pcap`它通过监听接口`wlo1`（WiFi接口）来捕获数据包，并将数据包写入目标位置`data.pcap`。它将持续进行捕获，直到用户按下CTRL-C键中断捕获为止。
* `tcpdump -i any -nn`捕获所有接口上的数据包，并在屏幕上显示它们，但不解析域名或协议。


### **按主机筛选**

假设只对与网络打印机或特定游戏服务器交换的 IP 数据包感兴趣。您可以使用 \`--capture-packet\` 或 \`--capture-packet\` 轻松地将捕获的数据包限制在该主机上`host IP`。`host HOSTNAME`在下面的终端中，我们捕获了所有与该主机交换的数据包`example.com`，并将它们保存到\`/etc/hosts\` 文件中。需要注意的是，捕获数据包需要您以 \`/ etc/hosts\` 或 \`/etc/hosts\` 身份`http.pcap`登录。`rootsudo`

```bash
user@TryHackMe$ sudo tcpdump host example.com -w http.pcap
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
16:49:02.482295 IP 192.168.139.132.49480 > 93.184.215.14.http: Flags [S], seq 3330895816, win 32120, options [mss 1460,sackOK,TS val 621343956 ecr 0,nop,wscale 7], length 0
16:49:02.635087 IP 93.184.215.14.http > 192.168.139.132.49480: Flags [S.], seq 2231582859, ack 3330895817, win 64240, options [mss 1460], length 0
16:49:02.635125 IP 192.168.139.132.49480 > 93.184.215.14.http: Flags [.], ack 1, win 32120, length 0
16:49:02.635491 IP 192.168.139.132.49480 > 93.184.215.14.http: Flags [P.], seq 1:131, ack 1, win 32120, length 130: HTTP: GET / HTTP/1.1
16:49:02.635580 IP 93.184.215.14.http > 192.168.139.132.49480: Flags [.], ack 131, win 64240, length 0
[...]
^C
13 packets captured
25 packets received by filter
0 packets dropped by kernel
```

如果您想将数据包限制为来自特定源 IP 地址或主机名的数据包，则必须使用 \`--source-ip\` 或 \`--hostname\` `src host IP`。同样`src host HOSTNAME`，您可以使用 \`--destination-to `dst host IP`...`dst host HOSTNAME`


### **按端口过滤**

如果您想捕获所有__DNS__流量，可以将捕获的数据包限制在特定端口上`port 53`。请记住，__DNS__默认使用__UDP__和__TCP__端口 53。在下面的示例中，我们可以看到网卡读取的所有__DNS查询。下面的终端显示了两个DNS__查询：第一个查询请求 example.org 使用的 IPv4 地址，而第二个查询请求与 example.org 关联的 IPv6 地址。

```bash
user@TryHackMe$ sudo tcpdump -i ens5 port 53 -n
[sudo] password for strategos: 
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
17:26:33.591670 IP 192.168.139.132.47902 > 192.168.139.2.53: 47108+ A? example.org. (29)
17:26:33.591717 IP 192.168.139.132.47902 > 192.168.139.2.53: 5+ AAAA? example.org. (29)
17:26:33.593324 IP 192.168.139.2.53 > 192.168.139.132.47902: 47108 1/0/0 A 93.184.215.14 (45)
17:26:33.593325 IP 192.168.139.2.53 > 192.168.139.132.47902: 5 1/0/0 AAAA 2606:2800:21f:cb07:6820:80da:af6b:8b2c (57)
[...]
^C
12 packets captured
12 packets received by filter
0 packets dropped by kernel
```

可以使用 \`--source\`和\`--destination\` 分别将数据包限制为来自特定源端口号或特定目标端口号的数据包`dst port PORT_NUMBER`


### **按协议过滤**

我们将介绍的最后一种过滤类型是按协议过滤。您可以将数据包捕获限制为特定协议；例如：`ip`\`IP\`、`ip6`\`HTTP\`、`udp`\`HTTPS\`、 \`HTTPS\``tcp`和`icmp`\`HTTPS\`。在下面的示例中，我们将数据包捕获限制为 ICMP 数据包。我们可以看到 ICMP 回显请求和响应，这可能表明有人正在运行 \` `ping`HTTPS\` 命令。此外，还存在 ICMP 超时；这可能是由于运行 \`HTTPS\`命令造成的（如["网络基础知识"](https://tryhackme.com/r/room/networkingessentials)`traceroute`房间中所述）。

```bash
user@TryHackMe$ sudo tcpdump -i ens5 icmp -n
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
18:11:00.624681 IP 192.168.139.132 > 93.184.215.14: ICMP echo request, id 47038, seq 1, length 64
18:11:00.781482 IP 93.184.215.14 > 192.168.139.132: ICMP echo reply, id 47038, seq 1, length 64
18:11:04.168792 IP 192.168.139.2 > 192.168.139.132: ICMP time exceeded in-transit, length 68
18:11:04.168815 IP 192.168.139.2 > 192.168.139.132: ICMP time exceeded in-transit, length 68
[...]
18:11:14.857188 IP 93.184.215.14 > 192.168.139.132: ICMP 93.184.215.14 udp port 33495 unreachable, length 68
^C
52 packets captured
52 packets received by filter
0 packets dropped by kernel
```

### **逻辑运算符**

三个非常有用的逻辑运算符：

* `and`捕获满足两个条件的包。例如，`tcpdump host 1.1.1.1 and tcp`捕获满足以下条件`tcp`的流量`host 1.1.1.1`。
* `or`：当满足任一条件时捕获数据包。例如，`tcpdump udp or icmp`捕获__UDP__或ICMP流量。
* `not`：当条件不成立时捕获数据包。例如，捕获除__TCP__`tcpdump not tcp`段之外的所有数据包；我们预期在结果中找到__UDP__、ICMP 和__ARP数据包。__

| **命令** | **解释** |
|----|----|
| `tcpdump host IP`或者`tcpdump host HOSTNAME` | 按 IP 地址或主机名过滤数据包 |
| `tcpdump src host IP`或者 | 按特定源主机过滤数据包 |
| `tcpdump dst host IP` | 按特定目标主机过滤数据包 |
| `tcpdump port PORT_NUMBER` | 按端口号过滤数据包 |
| `tcpdump src port PORT_NUMBER` | 按指定的源端口号过滤数据包 |
| `tcpdump dst port PORT_NUMBER` | 按指定目标端口号过滤数据包 |
| `tcpdump PROTOCOL` | 按协议过滤数据包；例如，\`http\` `ip`、`ip6`\`http\` 和 \`http\`。`icmp` |

### 示例

* `tcpdump -i any tcp port 22`监听所有接口并捕获`tcp`进出数据包`port 22`，即__SSH__流量。
* `tcpdump -i wlo1 udp port 123`监听 WiFi 网卡并将`udp`流量过滤到`port 123`网络时间协议 ( __NTP__ )。
* `tcpdump -i eth0 host example.com and tcp port 443 -w https.pcap`将会监听`eth0`有线以太网接口，并过滤与`example.com`使用该接口的流量`tcp`。`port 443`换句话说，此命令会过滤与该接口相关的 HTTPS 流量`example.com`。


可以写出：

* `tcpdump "tcp[tcpflags] == tcp-syn"`捕获**仅**设置了 SYN（同步）标志，而所有其他标志均未设置的__TCP__数据包。
* `tcpdump "tcp[tcpflags] & tcp-syn != 0"`捕获**至少**设置了 SYN（同步）标志的__TCP__数据包。
* `tcpdump "tcp[tcpflags] & (tcp-syn|tcp-ack) != 0"`捕获**至少**设置了SYN（同步）**或ACK（确认）标志的**__TCP__数据包。