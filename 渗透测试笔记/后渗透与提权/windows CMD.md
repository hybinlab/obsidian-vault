---
publish: true
tags:
  - 渗透测试
  - 后渗透与提权
---
Windows 目录的系统环境变量是`%windir%`

## HOSTNAME

**hostname**命令会输出计算机名称。

 ![](hostname.png " =266x56")

## WHOAMI

**whoami**命令会输出已登录用户的名称。

 ![](whoami.png " =260x49")


检索命令帮助手册的命令是 `/?`。

例如，要查看**ipconfig**的帮助手册，可以使用以下命令：`ipconfig /?`

 ![](ipconfig-help.png " =616x311")



:::info
**注意**：要清除命令提示符屏幕，命令是`cls`。 

:::


## NETSTAT

下一个命令是`netstat`。根据帮助手册，此命令将显示协议统计信息和当前 TCP/IP 网络连接。 

 ![](netstat.png " =643x209")

在上图中，红色方框内的线条展示了该命令的示例语法。 

该结构告诉我们**netstat**命令可以单独运行，也可以与参数一起运行，例如`-a`，，，  `-b`等等  `-e`。 

**当向根命令（本例中为 netstat）**添加任何参数时，输出结果都会发生变化。不妨尝试添加几个参数，亲自验证一下。 

该`net`命令主要用于管理网络资源。 该命令支持子命令。

如果你输入**net**而不带子命令，输出将显示 root 命令的语法，并显示一些你可以使用的子命令。

 ![](net.png " =564x131")

对于 net 命令，直接显示帮助手册`/?`是行不通的。在这种情况下，你需要使用不同的语法，即`net help`.

 ![](net-help.png " =617x376")

所以，如果您想查看的帮助信息`net user` ，命令是`net help user`。 

 ![](net-help-user2.png " =568x224")

您可以使用相同的命令查看其他有用的**net**子命令的帮助信息，例如**localgroup**、**use**、**share**和**session**。 


了解其他选项，可以运行命令`netstat -h`，其中`-h`会显示帮助页面。我们选择了以下选项：

* `-a`显示所有已建立的连接和监听端口
* `-b`显示与每个监听端口和已建立的连接关联的程序
* `-o`显示与连接关联的进程 ID ( __PID )__
* `-n`地址和端口号均采用数字形式

我们将这四个选项组合起来并执行`netstat -abon`命令

 ![](渗透测试笔记/uploads/e6d1e924-6404-478c-b58a-1a046b0538c8/6a50014c-7946-4923-a9a8-e21c9d6e77fc/image.png " =745x801")


## SET

```bash
# 显示所有环境变量
SET

# 显示特定环境变量
SET PATH
SET USERNAME
```

## VER

`ver`命令来确定操作系统（__OS__）版本

```bash
C:\>ver                                                                                                                                              
Microsoft Windows [Version 10.0.17763.1821]
```


## SYSINFO

`systeminfo`命令来列出系统的各种信息，例如__操作系统__信息、系统详情、处理器和内存。

```bash
C:\>systeminfo

Host Name:                 WIN-SRV-2019
OS Name:                   Microsoft Windows Server 2019 Datacenter
OS Version:                10.0.17763 N/A Build 17763
OS Manufacturer:           Microsoft Corporation
OS Configuration:          Standalone Server
OS Build Type:             Multiprocessor Free
[...]
```



:::info
如果输出内容过长，你可以使用管道将其输出。然后，你可以按空格键逐页查看。为了演示这一点，请尝试运行`driverquery`并与运行进行比较`driverquery | more`。在后者中，你可以逐页显示输出，并使用退出`CTRL + C`。

* `help`- 提供特定命令的帮助信息
* `cls`- 清除命令提示符屏幕。

:::


## nslookup

可以查找主机或域名并返回其 IP 地址


## dir

`dir`您可以使用.查看子目录。

 ![](渗透测试笔记/uploads/e6d1e924-6404-478c-b58a-1a046b0538c8/5be8a2cf-e178-4f04-812c-48bcbb232891/image.png " =414x254")

可以使用以下选项`dir`：

* `dir /a`- 同时显示隐藏文件和系统文件。
* `dir /s`- 显示当前目录及其所有子目录中的文件。


:::info
可以输入文字`tree`来直观地表示子目录和子子目录。

:::


要创建目录，使用`mkdir directory_name,mkdir`代表*创建目录*。要删除目录，请使用 \` `rmdir directory_name`;\`，\`;\``rmdir`代表*删除目录*。


## type

类似linux的cat


## move

类似linux的mv


## del

类似linux的rm


## tasklist

列出正在运行的进程

比如要搜索与sshd.exe相关的任务，可以使用命令tasklist /FI "imagename eq sshd.exe"。注意/FI参数用于设置"映像名称等于sshd.exe"的筛选条件。

```bash
C:\>tasklist /FI "imagename eq sshd.exe"

Image Name                     PID Session Name        Session#    Mem Usage
========================= ======== ================ =========== ============
sshd.exe                      2116 Services                   0      6,992 K
sshd.exe                      2712 Services                   0      7,668 K
sshd.exe                      4752 Services                   0      7,372 K
```

假设要删除一个进程：

```bash
taskkill /PID 进程号
```


## runas

提权用的


## driverquery

显示已安装的设备驱动程序列表