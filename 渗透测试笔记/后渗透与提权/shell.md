---
publish: true
tags:
  - 渗透测试
  - 后渗透与提权
---
## 查看当前shell

```powershell
user@tryhackme:~$ echo $SHELL
/bin/bash
```


## 查看有哪些shell

可以通过在终端中`/etc/shells`输入以下命令来列出 Linux 操作系统中可用的 shell

```powershell
user@tryhackme:~$ cat /etc/shells
# /etc/shells: valid login shells
/bin/sh
/bin/bash
/usr/bin/bash
/bin/rbash
/usr/bin/rbash
/bin/dash
/usr/bin/dash
/usr/bin/tmux
/usr/bin/screen
/bin/zsh
/usr/bin/zsh
```

__要在这些 shell 之间切换，您可以输入操作系统__中存在的 shell 名称

```powershell
user@tryhackme:~$ zsh
tryhackme% 
```


:::info
如果想永久更改默认 shell，可以使用以下命令：`chsh -s /usr/bin/zsh`

:::


## 自动化脚本

要执行脚本，我们首先需要确保脚本具有执行权限

```powershell
user@tryhackme:~$ chmod +x first_script.sh
```