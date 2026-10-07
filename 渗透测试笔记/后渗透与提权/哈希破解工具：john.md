---
publish: true
tags:
  - 渗透测试
  - 后渗透与提权
---
## 安装

```bash
sudo apt install john
```

或

```bash
sudo dnf install john
```

`/usr/share/wordlists`目录包含一系列优秀的字典文件,如`rockyou.txt`


## 语法

John 内置了检测哈希类型并选择相应规则和格式进行破解的功能；虽然这种方法并非总是最佳选择，因为它可能不太可靠，但如果您无法识别哈希类型并想尝试破解，这不失为一个好办法！为此，我们使用以下语法：

`john --wordlist=[path to wordlist] [path to file]`

* `--wordlist=`：指定使用单词列表模式，从您提供的路径中的文件中读取数据。
* `[path to wordlist]`：您正在使用的单词列表的路径，如上一个任务中所述。

**用法示例：**

`john --wordlist=/usr/share/wordlists/rockyou.txt hash_to_crack.txt`



| **哈希类型** | **正确格式名** | **示例命令** |
|----|----|----|
| MD5（裸哈希） | `Raw-MD5` | `john --format=raw-md5 --wordlist=...` |
| SHA1（裸哈希） | `Raw-SHA1` | `john --format=raw-sha1 --wordlist=...` |
| SHA256（裸哈希） | `Raw-SHA256` | `john --format=raw-sha256 --wordlist=...` |
| NTLM（Windows） | `NT` | `john --format=nt --wordlist=...` |
| Linux shadow | `sha512crypt` | `john --format=sha512crypt --wordlist=...` |
| bcrypt | `bcrypt` | `john --format=bcrypt --wordlist=...` |



:::info
`/etc/shadow`是Linux系统上存储密码哈希值的文件

:::


## 破解 /etc/shadow 哈希值

John_password_company 的基本语法`unshadow`如下：

`unshadow [path to passwd] [path to shadow]`

* `[path to passwd]/etc/passwd`：包含从目标计算机获取的文件副本的文件。
* `[path to shadow]/etc/shadow`：包含从目标计算机获取的文件副本的文件。

**用法示例：**

`unshadow local_passwd local_shadow > unshadowed.txt`


## 自定义规则


## 破解受密码保护的压缩文件

使用`zip2john`工具将 Zip 文件转换为 John 可以理解并希望能够破解的哈希格式。主要用法如下：

`zip2john [options] [zip file] > [output file]`

* `[options]`允许您传递特定的校验和选项`zip2john`；这通常没有必要。
* `[zip file]`：要获取哈希值的 Zip 文件的路径
* `>`这会将此命令的输出重定向到另一个文件
* `[output file]`这是用于存储输出结果的文件。

**用法示例**

`zip2john zipfile.zip > zip_hash.txt`

之后再进行上面破解的操作

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt rar_hash.txt
```


## 破解受密码保护的 RAR 压缩文件

使用该`rar2john`工具将 RAR 文件转换为 John 可以理解的哈希格式。基本语法如下：

`rar2john [rar file] > [output file]`

* `rar2john`：调用该`rar2john`工具
* `[rar file]`：您要获取哈希值的 RAR 文件的路径
* `>`这会将此命令的输出重定向到另一个文件
* `[output file]`这是用于存储命令输出的文件。

**用法示例**

`/opt/john/rar2john rarfile.rar > rar_hash.txt`


### **破解__SSH__密钥密码**

`ssh2john [id_rsa private key file] > [output file]`

* `ssh2john`：调用该`ssh2john`工具
* `[id_rsa private key file]`：要获取哈希值的 id_rsa 文件的路径
* `>`这是输出导向器。我们用它来将此命令的输出重定向到另一个文件。
* `[output file]`这是用于存储输出结果的文件。

最后，我们将 ssh2john 输出的文件（在我们的示例用例中称为 \`.ssh2john.js\`）提供给 John `id_rsa_hash.txt`，就像我们之前对 \`.ssh2john.js\` 所做的那样`rar2john`，我们可以无缝地将其与 John 一起使用：

`john --wordlist=/usr/share/wordlists/rockyou.txt id_rsa_hash.txt`