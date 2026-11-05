---
publish: true
tags:
  - macOS
  - Ghostty
  - SSH
  - 排障
---

> 整理：2026-11-05。场景：Mac 使用 Ghostty，通过 SSH 登录 Ubuntu VM，`clear`、`nano` 提示不认识 `xterm-ghostty`。
> 参考：[Ghostty 官方 Terminfo / SSH 说明](https://ghostty.org/docs/help/terminfo#ssh)。

## 现象与原因

```text
root@docker-host:~# clear
'xterm-ghostty': unknown terminal type.

root@docker-host:~# nano
Error opening terminal: xterm-ghostty.
```

Ghostty 使用 `TERM=xterm-ghostty` 表示自己的终端能力。SSH 将终端类型传给远端，但 VM 的 terminfo 数据库可能没有对应条目，依赖 ncurses 的程序就无法初始化界面。

本次排查的 agent 是 Ubuntu 24.04、ncurses 6.4，即使已经安装 `ncurses-term`，仍缺少该条目。官方说明较新的 ncurses 数据库才包含 Ghostty，因此在旧发行版上仅安装 `ncurses-term` 不一定解决问题。

## 临时恢复当前会话

在报错的 **VM 终端**执行：

```bash
export TERM=xterm-256color
clear
nano
```

这是当前 shell 的兼容回退，新 SSH 会话仍可能收到 `xterm-ghostty`。若只是临时清屏，不想修改当前 shell 的变量，可以运行 `TERM=xterm-256color clear`。

长期使用建议补齐 terminfo；回退为 `xterm-256color` 不能完整表达 Ghostty 的扩展能力。

## 永久修复：从 Mac 导出，交给远端安装

以下传输命令在 **Mac 本地的 Ghostty 窗口**执行，不是在已登录的 VM 中执行。

### 使用远端默认安装位置

```bash
infocmp -x xterm-ghostty | ssh root@docker-host -- tic -x -
```

处理过程：

1. 本地 `infocmp -x` 导出 Ghostty 的终端描述，包括扩展能力。
2. SSH 将文本通过标准输入传给远端。
3. 远端 `tic -x -` 编译并安装 terminfo。

`docker-host` 必须是 Mac 能解析的主机名或 SSH 别名；否则替换成 IP，例如 `root@192.168.31.1`。

root 通常可以安装到系统 terminfo 数据库，供其他用户使用。但默认位置也受 `TERMINFO`、编译配置和目录权限影响，不能只凭 root 身份断言落盘位置。

### 明确指定系统级安装

远端使用 root 登录时，可以明确写入系统目录：

```bash
infocmp -x xterm-ghostty | ssh root@192.168.31.1 \
  'tic -x -o /usr/share/terminfo -'
```

适合多个账号都需要使用 Ghostty 的 VM。

### 明确指定用户级安装

```bash
infocmp -x xterm-ghostty | ssh root@192.168.31.1 \
  'tic -x -o ~/.terminfo -'
```

此时安装到远端 root 的 `~/.terminfo`，主要供该账号使用。换成其他 SSH 登录用户，就是安装到那个用户的目录。无需系统目录写权限。

远端缺少 `tic` 时，在 Ubuntu 上先安装：

```bash
apt update
apt install -y ncurses-bin
```

普通账号需要通过有权限的方式安装软件包；用户级 terminfo 的编译本身不要求 root。

## 批量处理多台 VM

先在 **Mac 本地 Ghostty** 导出一份：

```bash
infocmp -x xterm-ghostty > /tmp/xterm-ghostty.terminfo
test -s /tmp/xterm-ghostty.terminfo
```

确认导出无报错、文件非空后，再运行批量安装。下例使用用户级目录：

```bash
for host in \
  root@192.168.31.1 \
  root@192.168.31.3 \
  root@192.168.31.4 \
  root@192.168.31.5 \
  root@192.168.31.6 \
  root@192.168.31.12 \
  root@192.168.31.13 \
  root@192.168.31.14
do
  echo "安装到 $host"
  ssh "$host" \
    'tic -x -o ~/.terminfo - && infocmp -x xterm-ghostty >/dev/null' \
    < /tmp/xterm-ghostty.terminfo
done
```

按实际机器调整列表；每台都需要已有可用的 SSH 登录方式。上述列表对应既有核心 Linux VM 与三台 Kubernetes 节点，不包含 Windows 和此前 SSH 认证失败的 archvm。

完成后 `/tmp/xterm-ghostty.terminfo` 只是可清理的导出副本，远端运行不再依赖它。

## 验证

重新 SSH 登录目标 VM，执行：

```bash
echo "$TERM"
infocmp -x xterm-ghostty >/dev/null
clear
nano
```

正常结果：`TERM` 为 `xterm-ghostty`，`infocmp` 无报错，`clear`、`nano` 正常显示。

如果此前执行过临时回退，又不想重新登录，可在安装成功后运行 `export TERM=xterm-ghostty` 再验证。不需要重启 VM。

需要确认安装位置时，直接运行 `infocmp -x xterm-ghostty`，输出开头通常会标出实际读取的文件。也可以检查 `/usr/share/terminfo` 和 `~/.terminfo`；不同系统的条目子目录可能采用字符或十六进制命名，不必只查 `x/`。

## 常见问题

| 现象 | 处理 |
|---|---|
| Mac 本地 `infocmp` 也找不到条目 | 确认是在本地 Ghostty 窗口执行，不是远端 SSH 内；检查本地 Ghostty 安装及 terminfo 环境 |
| Mac 导出的内容出现大量 `Illegal character` | 旧 macOS 自带 ncurses 可能过旧，改用 Homebrew 的 `infocmp` |
| 远端提示 `tic: command not found` | 安装远端的 `ncurses-bin` |
| 用户级安装后，另一个账号仍报错 | 为该账号安装，或使用系统级安装 |
| 提示旧 `tic` 可能将 description 当作 alias | 官方说明该特定警告可以忽略；仍以 `infocmp` 和程序实测结果为准 |
| 通过 sudo 运行程序时才报错 | 检查目标账号能否找到条目，以及 sudo 是否保留所需的 `TERMINFO` 环境；可考虑系统级安装 |

Mac 上需要新版 `infocmp` 时：

```bash
brew install ncurses
"$(brew --prefix ncurses)/bin/infocmp" -x xterm-ghostty \
  > /tmp/xterm-ghostty.terminfo
```

确认导出成功后重新执行批量安装步骤。`brew --prefix ncurses` 可避免硬编码 Apple Silicon 与 Intel Mac 不同的 Homebrew 路径。

修复后保留 Ghostty 自己设置的 `TERM`，不必在所有机器的 `.bashrc` 中永久强制写入 `xterm-256color`。Terminfo 解决终端能力描述问题；宠物动画等图形功能，还取决于终端协议及中间连接链路。

相关：[[Ghostty 常用快捷键与使用技巧]]、[[Homebrew 使用指南]]、[[Homelab SSH 密钥认证与管理 SOP]]、[[Pets（宠物与氛围互动）]]。
