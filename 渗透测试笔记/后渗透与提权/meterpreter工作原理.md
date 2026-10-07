---
publish: true
tags:
  - 渗透测试
  - 后渗透与提权
---
## msfconsole3

__meterpreter__在目标系统上运行，但并未安装在目标系统上。它在内存中运行，不会将自身写入目标系统的磁盘。

此特性旨在避免被杀毒软件检测到。默认情况下，大多数杀毒软件会扫描磁盘上的新文件（例如，当您从互联网下载文件时）。Meterpreter__在__内存（__RAM__ - 随机存取存储器）中运行，以避免在目标系统上留下需要写入磁盘的文件（例如__meterpreter.exe__）。这样，__Meterpreter__将被识别为一个进程，而不会在目标系统上留下任何文件。

__Meterpreter还旨在通过使用与运行Metasploit__的服务器（通常是您的攻击机）的加密通信来避免被基于网络的入侵防御系统 ( __IPS ) 和入侵检测系统 ( IDS__ ) 解决方案检测到。如果目标组织不解密和检查进出本地网络的加密流量（例如 HTTPS），__IPS__和__IDS__解决方案将无法检测到其活动。


:::info
大多数杀毒软件都能检测到它

:::


__Metasploit__有效载荷最初可以分为两类：内联（也称为单级）和分阶段

分阶段有效载荷分两步发送到目标系统。首先安装初始部分（分阶段组件），然后请求__剩余__的有效载荷。这样可以减小初始有效载荷的大小

内联有效载荷则一步发送完成


使用`msfvenom --list payloads` 命令并搜索了"meterpreter"有效载荷（`| grep meterpreter`在命令行中添加了该参数），因此输出仅显示这些有效载荷

```bash
root@ip-10-10-186-44:~# msfvenom --list payloads | grep meterpreter
    android/meterpreter/reverse_http                    Run a meterpreter server in Android. Tunnel communication over HTTP
    android/meterpreter/reverse_https                   Run a meterpreter server in Android. Tunnel communication over HTTPS
    android/meterpreter/reverse_tcp                     Run a meterpreter server in Android. Connect back stager
    android/meterpreter_reverse_http                    Connect back to attacker and spawn a Meterpreter shell
    android/meterpreter_reverse_https                   Connect back to attacker and spawn a Meterpreter shell
    android/meterpreter_reverse_tcp                     Connect back to the attacker and spawn a Meterpreter shell
    apple_ios/aarch64/meterpreter_reverse_http          Run the Meterpreter / Mettle server payload (stageless)
    apple_ios/aarch64/meterpreter_reverse_https         Run the Meterpreter / Mettle server payload (stageless)
    apple_ios/aarch64/meterpreter_reverse_tcp           Run the Meterpreter / Mettle server payload (stageless)
    apple_ios/armle/meterpreter_reverse_http            Run the Meterpreter / Mettle server payload (stageless)
    apple_ios/armle/meterpreter_reverse_https           Run the Meterpreter / Mettle server payload (stageless)
    apple_ios/armle/meterpreter_reverse_tcp             Run the Meterpreter / Mettle server payload (stageless)
    java/meterpreter/bind_tcp                           Run a meterpreter server in Java. Listen for a connection
    java/meterpreter/reverse_http                       Run a meterpreter server in Java. Tunnel communication over HTTP
    java/meterpreter/reverse_https                      Run a meterpreter server in Java. Tunnel communication over HTTPS
    java/meterpreter/reverse_tcp                        Run a meterpreter server in Java. Connect back stager
    linux/aarch64/meterpreter/reverse_tcp               Inject the mettle server payload (staged). Connect back to the attacker
    linux/aarch64/meterpreter_reverse_http              Run the Meterpreter / Mettle server payload (stageless)
    linux/aarch64/meterpreter_reverse_https             Run the Meterpreter / Mettle server payload (stageless)
    linux/aarch64/meterpreter_reverse_tcp               Run the Meterpreter / Mettle server payload (stageless)
    linux/armbe/meterpreter_reverse_http                Run the Meterpreter / Mettle server payload (stageless)
    linux/armbe/meterpreter_reverse_https               Run the Meterpreter / Mettle server payload (stageless)
    linux/armbe/meterpreter_reverse_tcp                 Run the Meterpreter / Mettle server payload (stageless)
    linux/armle/meterpreter/bind_tcp                    Inject the mettle server payload (staged). Listen for a connection
    linux/armle/meterpreter/reverse_tcp                 Inject the mettle server payload (staged). Connect back to the attacker [...]
```


决定使用哪个版本的__Meterpreter__主要取决于三个因素；

* 目标操作系统（目标操作系统是__Linux__还是Windows？是Mac设备？是安卓手机？等等）
* 目标系统上可用的组件（是否安装了 Python？这是一个__PHP__网站吗？等等）
* 您可以与目标系统建立哪些网络连接类型（是否允许原始__TCP__连接？是否只能建立 HTTPS 反向连接？IPv6 地址的监控是否不如 IPv4 地址严格？等等） 


## meterpreter命令

`help` 在任何 Meterpreter 会话中（`meterpreter>`在提示符处显示）都将列出所有可用命令。

```bash
meterpreter > help

Core Commands
=============

    Command                   Description
    -------                   -----------
    ?                         Help menu
    background                Backgrounds the current session
    bg                        Alias for background
    bgkill                    Kills a background meterpreter script
    bglist                    Lists running background scripts
    bgrun                     Executes a meterpreter script as a background thread
    channel                   Displays information or control active channels
    close                     Closes a channel[...]
```


__Meterpreter__提供三大类工具:

* Built-in commands
* __Meterpreter__ tools
* __Meterpreter__ scripting


`getuid`当前运行 所用的用户

```bash
meterpreter > getuid
Server username: NT AUTHORITY\SYSTEM
meterpreter >
```


**Migrate**使__Meterpreter能够像键盘记录器__一样工作。迁移到另一个进程还有助于获得更稳定的__Meterpreter__会话。

要迁移到任何进程，您需要输入 migrate 命令，后跟目标进程的__PID 。以下示例展示了Meterpreter__迁移到进程 ID 716 的过程。 

```bash
meterpreter > migrate 716
[*] Migrating from 1304 to 716...
[*] Migration completed successfully.
meterpreter >
```


search可用于查找可能包含重要信息的文件


:::info
在 CTF 比赛中，它可以用于快速查找 flag 或证明文件；而在实际渗透测试中，您可能需要搜索用户生成的文件或配置文件，这些文件可能包含密码或帐户信息。

:::

```bash
meterpreter > search -f flag2.txt
Found 1 result...
    c:\Windows\System32\config\flag2.txt (34 bytes)
meterpreter >
```


shell命令会在目标系统上启动一个常规的命令行 shell。按下 CTRL+Z 可以返回到__Meterpreter__ shell。

```bash
meterpreter > shell
Process 2124 created.
Channel 1 created.
Microsoft Windows [Version 6.1.7601]
Copyright (c) 2009 Microsoft Corporation.  All rights reserved.

C:\Windows\system32>
```


\

:::success
房间攻略

<https://medium.com/@saltyxcoconut/metasploit-meterpreter-tryhackme-walkthrough-0aeb618010e6>

:::


\