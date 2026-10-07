---
publish: true
tags:
  - 渗透测试
  - 信息收集
---
## 💻 Gobuster：目录爆破工具概览

**Gobuster** 是一款用 Golang 编写的开源攻击性工具。它通过**暴力破解**的方式，利用特定的\*\*字典文件（wordlists）**并处理传入的响应，来枚举 Web 目录、DNS 子域名、虚拟主机（vhosts）、Amazon S3 存储桶和 Google Cloud Storage。许多安全专业人员使用此工具进行渗透测试、漏洞赏金狩猎和网络安全评估。从道德黑客攻击的阶段来看，我们可以将 Gobuster 置于**侦察（reconnaissance）**和**扫描（scanning）\*\*阶段之间。

在深入探索 Gobuster 之前，让我们简要讨论一下**枚举**和**暴力破解**的概念。


-----

### 📚 枚举 (Enumeration)

**枚举**是列出所有可用资源（无论是否可访问）的行为。例如，Gobuster 枚举 Web 目录。

### 🔨 暴力破解 (Brute Force)

**暴力破解**是尝试所有可能性直到找到匹配项的行为。这就像拥有十把钥匙并在一把锁上全部尝试，直到找到合适的为止。Gobuster 利用**字典文件**来实现此目的。


-----

## 🔎 Gobuster 概览

Gobuster 默认包含在 **Kali Linux** 等发行版中。让我们从查看 Gobuster 的帮助页面开始。这个帮助页面为我们提供了其功能和选项的良好概览。

输入以下命令：`gobuster --help`。您应该会看到 Gobuster 工具的帮助页面，如下所示：

```bash
AttackBox Terminal
root@tryhackme:~# gobuster --help
Usage:
  gobuster [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell
  dir         Uses directory/file enumeration mode
  dns         Uses DNS subdomain enumeration mode
  fuzz        Uses fuzzing mode. Replaces the keyword FUZZ in the URL, Headers and the request body
  gcs         Uses gcs bucket enumeration mode
  help        Help about any command
  s3          Uses aws bucket enumeration mode
  tftp        Uses TFTP enumeration mode
  version     shows the current version
  vhost       Uses VHOST enumeration mode (you most probably want to use the IP address as the URL parameter)

Flags:
      --debug                 Enable debug output
      --delay duration        Time each thread waits between requests (e.g. 1500ms)
  -h, --help                  help for gobuster
      --no-color              Disable color output
      --no-error              Don't display errors
  -z, --no-progress           Don't display progress
  -o, --output string         Output file to write results to (defaults to stdout)
  -p, --pattern string        File containing replacement patterns
  -q, --quiet                 Don't print the banner and other noise
  -t, --threads int           Number of concurrent threads (default 10)
  -v, --verbose               Verbose output (errors)
  -w, --wordlist string       Path to the wordlist. Set to - to use STDIN.
      --wordlist-offset int   Resume from a given position in the wordlist (defaults to 0)

Use "gobuster [command] --help" for more information about a command.
```

帮助页面包含多个部分：

* **Usage (用法):** 展示了使用命令的语法。
* **Available Commands (可用命令):** 提供了多个命令，帮助我们枚举目录、文件、DNS 子域名、Google Cloud Storage 存储桶和 Amazon AWS S3 存储桶。在本房间中，我们将重点关注 `**dir**`、`**dns**` 和 `**vhost**` 命令。我们将在后续任务中介绍它们。
* **Flags (标志/选项):** 这些是我们可以配置的特定选项，用于自定义我们的命令。让我们看看在本房间中我们将经常使用的标志：

| 短标志 | 长标志 | 描述 |
|:---|:---|:---|
| `**-t**` | `**--threads**` | 此标志配置用于扫描的**线程数**。每个线程都会以轻微延迟发送请求。默认线程数是 **10**。当使用大型字典时，此数字可能较慢。您可以根据可用的系统资源增加或减少线程数。 |
| `**-w**` | `**--wordlist**` | 此标志配置要用于迭代的**字典文件路径**。字典中的每个条目都会附加到您在命令中包含的 URL 上。 |
|    | `**--delay**` | 此标志定义发送请求之间等待的**时间量**。某些 Web 服务器包含检测枚举的机制，通过查看在特定时间段内收到的请求数量。我们可以增加后续请求之间的延迟，使其看起来像正常的 Web 流量。 |
|    | `**--debug**` | 当命令给出意外错误时，此标志可帮助我们进行**故障排除**。 |
| `**-o**` | `**--output**` | 此标志将枚举结果**写入**我们选择的文件中。 |


-----

## 💡 示例

让我们看一个示例，了解如何将这些命令和标志结合使用来枚举 Web 目录：

```bash
gobuster dir -u "http://www.example.thm/" -w /usr/share/wordlists/dirb/small.txt -t 64
```

* `**gobuster dir**`：表示我们将使用**目录和文件枚举模式**。
* `**-u "http://www.example.thm/"**`：告诉 Gobuster 目标 URL 是 `http://example.thm/`。
* `**-w /usr/share/wordlists/dirb/small.txt**`：指示 Gobuster 使用 `**small.txt**` **字典文件**来暴力破解 Web 目录。Gobuster 将使用字典中的每个条目来构成新的 URL 并向该 URL 发送 GET 请求。如果字典的第一个条目是 `images`，Gobuster 将向 `http://example.thm/images/` 发送一个 GET 请求。
* `**-t 64**`：将 Gobuster 将使用的**线程数设置为 64**。这大大提高了性能。

现在我们对 Gobuster 有了一个快速概览，让我们在后续任务中探索不同的模式及其使用案例。


好的，这是原文内容的中文翻译和整理，以便于您做笔记。


-----

## 🎯 vhost 模式简介

* **vhost 模式**（Virtual Host Mode）：允许 Gobuster **暴力破解虚拟主机名**。
* **虚拟主机 (Virtual Hosts)**：在**同一台服务器/IP 地址上**运行的不同网站。
  * 它们有时看起来像子域名，但它们是**基于 IP 地址**运行在同一服务器上的。
  * **子域名 (Subdomains)** 是在 **DNS** 中设置的。
* **vhost 模式 与 dns 模式 的区别**：在于 Gobuster 扫描的方式。
  * **vhost 模式**：通过结合配置的 **HOSTNAME** (`-u` 标志) 和字典中的条目来创建 URL 并进行导航（例如，`http://<IP_ADDRESS>`，并在请求头中修改 Host:）。
  * **dns 模式**：通过结合配置的 **域名** (`-d` 标志) 和字典中的条目来创建 **FQDN**（完全限定域名），然后进行 **DNS 查询**。


-----

### ⚙️ vhost 模式常用标志 (Flags)

| 短标志 | 长标志 | 描述 |
|:---:|:---:|:---|
| `-u` | `--url` | 指定用于暴力破解虚拟主机名的 **基础 URL (目标 IP/域名)**。 |
|    | `--append-domain` | 将基础域名附加到字典中的每个单词（例如，`word.example.com`）。 |
| `-m` | `--method` | 指定用于请求的 **HTTP 方法** (例如, GET, POST)。 |
|    | `--domain` | **追加一个域名**到字典中的每个条目以形成一个有效的主机名（如果没有在 URL 中明确提供，此项有用）。 |
|    | `--exclude-length` | 根据响应主体的**长度**排除结果（用于过滤掉不想要的响应，如**误报/False Positives**）。 |
| `-r` | `--follow-redirect` | **跟随 HTTP 重定向**（在子域名可能重定向的情况下很有用）。 |

* **查看帮助页**：`gobuster vhost --help`


-----

### 📝 如何使用 vhost 模式

#### 1. 基本用法

```bash
gobuster vhost -u "http://example.thm" -w /path/to/wordlist
```

* `**-u**` 和 `**-w**` 标志是 vhost 枚举所必需的。

#### 2. 实用示例（更复杂的命令）

```bash
gobuster vhost -u "http://MACHINE_IP" --domain example.thm -w /usr/share/wordlists/SecLists/Discovery/DNS/subdomains-top1million-5000.txt --append-domain --exclude-length 250-320
```

* **注意**：在没有完整 DNS 基础架构的情况下，通常需要额外的标志，如 `--domain` 和 `--append-domain`。


-----

### 🌐 vhost 模式的工作原理

Gobuster 通过发送 **HTTP GET 请求** 并不断更改请求中的 `**Host:**` **头部** 来工作。

* **基本 GET 请求结构示例**：

  ```http
  GET / HTTP/1.1
  Host: www.example.thm  <- Gobuster 会修改的部分
  User-Agent: gobuster/3.6
  ...
  ```
* `**Host:**` **头部分解 (以** `**www.example.thm**` **为例)**:

  
  1. `**www**`：这是**子域/字典条目**。Gobuster 会用字典中的每个条目来填充这部分。
  2. `**.example**`：这是**二级域名**。可以通过 `**--domain**` **标志** 配置 (需与顶级域名一起配置)。
  3. `**.thm**`：这是**顶级域名**。可以通过 `**--domain**` **标志** 配置 (需与二级域名一起配置)。

#### **核心标志详解**

* `**gobuster vhost**`：指示 Gobuster 执行虚拟主机枚举。
* `**-u "http://MACHINE_IP"**`：设置要浏览的 URL 为目标 IP 地址。
* `**-w /path/to/wordlist**`：配置要使用的字典文件。
  * Gobuster 将字典中的每个条目附加到配置的域名上。
  * 如果未使用 `--domain` 明确配置域名，Gobuster 会尝试从 `-u` URL 中提取。
* `**--domain example.thm**`：将请求的 `Host:` 部分中的顶级和二级域名设置为 `example.thm`。
* `**--append-domain**`：**必须配置**，它将配置的域名附加到字典中的每个条目。
  * **如果不配置**，设置的主机名将只有 `www`、`blog` 等，导致命令运行不正确并显示**误报**。
* `**--exclude-length**`：过滤掉响应体长度范围内的结果，用于**过滤误报 (False Positives)**。
  * 误报通常具有**相似的响应大小**，通过排除这些长度可以筛选它们。
  * 期望得到 `**Status: 200**` **(OK)** 响应来确认**真报 (True Positive)**。