---
publish: true
tags:
  - macOS
  - Ghostty
  - 终端
---

> 整理：2026-11-05。面向 Mac 上使用 Ghostty、本地开发与 SSH 管理多台 VM 的场景。
> 下表按官方默认键位整理；不同版本、键盘布局及个人配置可能影响实际行为，以本机菜单和绑定列表为准。

## 先记住这几个

| 快捷键 | 用途 |
|---|---|
| `⌘ T` | 新建标签页 |
| `⌘ D` | 在右侧新建分屏，左右并排 |
| `⌘ ⇧ D` | 在下方新建分屏，上下排列 |
| `⌘ ⌥ 方向键` | 切换到对应方向的分屏 |
| `⌘ ⇧ Enter` | 放大当前分屏；再按恢复布局 |
| `⌘ W` | 关闭当前终端区域；有分屏时关闭当前分屏 |
| `⌘ ⇧ P` | 打开命令面板，查找可用操作 |
| `⌘ ,` | 打开配置文件 |
| `⌘ ⇧ ,` | 重新加载配置 |

符号对应：`⌘` = Command，`⌥` = Option，`⇧` = Shift，`⌃` = Control。配置中的 `super` / `cmd` 对应 Command，`alt` 对应 Option。

## 窗口、标签页与分屏

| 快捷键 | 用途 |
|---|---|
| `⌘ N` | 新建窗口 |
| `⌘ T` | 新建标签页 |
| `⌃ Tab` / `⌃ ⇧ Tab` | 下一个 / 上一个标签页 |
| `⌘ ⇧ ]` / `⌘ ⇧ [` | 下一个 / 上一个标签页 |
| `⌘ 1`～`⌘ 8` | 切换到对应序号标签页 |
| `⌘ 9` | 切换到最后一个标签页 |
| `⌘ D` / `⌘ ⇧ D` | 向右 / 向下分屏 |
| `⌘ ]` / `⌘ [` | 下一个 / 上一个分屏 |
| `⌘ ⌥ 方向键` | 按方向切换分屏 |
| `⌘ ⌃ 方向键` | 调整分屏大小 |
| `⌘ ⌃ =` | 均分分屏大小 |
| `⌘ ⇧ Enter` | 切换当前分屏放大状态 |
| `⌘ Enter` | 切换窗口全屏 |
| `⌘ W` | 关闭当前终端区域 |
| `⌘ ⌥ W` | 关闭当前标签页，包括里面的分屏 |
| `⌘ ⇧ W` | 关闭当前窗口 |
| `⌘ Q` | 退出 Ghostty |

放大分屏不会关闭其他分屏。关闭终端区域则可能断开其中的 SSH；需要保留远端任务时，见下文的 tmux 用法。

## 复制、查找与显示

| 快捷键 | 用途 |
|---|---|
| `⌘ C` / `⌘ V` | 复制选中文本 / 粘贴 |
| `⌘ A` | 选择终端内容，不是只选当前命令行 |
| `⌘ F` | 搜索终端历史输出；旧版可能不支持，检查菜单或升级 |
| `⌘ G` / `⌘ ⇧ G` | 下一个 / 上一个搜索结果 |
| `Esc` | 搜索激活时退出搜索 |
| `⌘ =` / `⌘ -` | 放大 / 缩小字体 |
| `⌘ 0` | 恢复配置的字号 |
| `⌘ K` | 清除屏幕及回滚历史，清除后不能再向上翻看这些输出 |
| `⌘ ↑` / `⌘ ↓` | 跳到上一个 / 下一个命令提示符，需要 shell integration |

搜索只针对当前终端保留的输出，不会搜索服务器磁盘上的日志文件。查完整日志仍应使用 `journalctl`、`less`、`rg` 等工具。

SSH 内的提示符跳转需要远端 shell 提供相应标记；本地可用不代表所有 VM 中都可用。

## Shell 本身也有一组常用键

下面是 Bash / Zsh 常见 Emacs 编辑模式下的操作，通常也适用于 SSH 内。它们由当前 shell 或前台程序处理；使用 Vi 编辑模式、nano、Vim 等时含义可能不同。

| 快捷键 | 用途 |
|---|---|
| `⌃ A` / `⌃ E` | 光标移到命令行开头 / 结尾 |
| `⌃ U` / `⌃ K` | 删除光标之前 / 之后的输入 |
| `⌃ W` | 删除前一个词 |
| `⌃ R` | 反向搜索历史命令，继续按可找更早记录 |
| `⌃ L` | 重绘 / 清屏，通常保留可回滚历史 |
| `⌃ C` | 中断当前前台命令，或取消当前输入 |
| `⌃ D` | 空命令行时发送 EOF，可能退出 shell 或当前 SSH |
| `⌃ Z` | 挂起前台任务；输入 `fg` 可恢复 |
| `Tab` | 补全命令、路径等 |

复制用 `⌘ C`，中断命令用 `⌃ C`。`⌃ L` 和 `⌘ K` 也不相同，排查问题时需要保留输出就避免清掉回滚历史。

## 管理多台 VM 的实用方式

### 标签页分主机，分屏做对照

日常可以给 PVE、Docker-Host、Agent 分别开标签页；需要同时观察应用和日志时，再在一个标签页中分屏。

例如排查 Docker 服务：

1. 在一个区域 SSH 登录 Docker-Host，执行 `docker logs -f <容器名>`。
2. 按 `⌘ D`，在新区域单独执行 SSH 登录，再运行检查或操作命令。
3. 用 `⌘ ⌥ ←/→` 切换，用 `⌘ ⇧ Enter` 临时放大日志区域。
4. 结束日志跟踪用 `⌃ C`，不必关闭整个标签页。

新建分屏不等于复制当前远端 SSH 会话；把每个分屏当作独立终端，需要时分别登录目标主机。执行改动前先核对提示符，必要时运行 `hostname`。

### SSH 别名保存在 Mac 上

在 **Mac 本地**的 `~/.ssh/config` 添加别名，例如：

```sshconfig
Host docker-host
    HostName 192.168.31.1
    User root

Host agent
    HostName 192.168.31.4
    User root
```

之后直接运行 `ssh docker-host` 或 `ssh agent`。已有同名条目时修改原条目，避免重复添加；认证继续沿用现有密钥配置。

### 长任务放在远端 tmux 中

Ghostty 的标签页和分屏负责本地布局。需要 SSH 断开后还能继续的交互任务，可以在 **目标 VM** 上使用已安装的 tmux：

```bash
tmux new -s work
# 在这里运行任务
```

按 `Ctrl+B`，松开后按 `D`，可离开会话并让任务继续。重新 SSH 登录同一台 VM 后运行：

```bash
tmux attach -t work
```

tmux 能应对连接断开，不能让任务跨 VM 重启继续运行。长期服务仍交给 systemd、Docker 等服务管理方式。

### SSH 终端类型报错先修 terminfo

如果 `clear`、`nano` 提示不认识 `xterm-ghostty`，按 [[Ghostty SSH 终端类型报错修复]] 处理。快捷键清屏不能解决远端终端能力描述缺失的问题。

## 配置与个性化

先按 `⌘ ,` 打开 Ghostty 实际使用的配置文件，避免猜测不同版本的文件路径。可以从少量配置开始：

```ini
font-size = 14
window-padding-x = 8
window-padding-y = 8

# 以下是可选的自定义绑定，不是默认快捷键
keybind = cmd+shift+e=equalize_splits
```

保存后按 `⌘ ⇧ ,` 重载。部分选项需要新建终端或重启应用，以该选项官方说明为准。若手动调整过字号，先按 `⌘ 0` 恢复配置字号，再观察效果。

需要用 Option 执行 Shell 的 Alt 操作时，可以按需设置：

```ini
macos-option-as-alt = true
```

这会改变 Option 组合键的行为，也会影响原本通过 Option 输入特殊字符的习惯；没有需要可保持默认。

### 查询本机版本和实际键位

以下命令在 **Mac 本地**执行，SSH 进去的 Linux VM 通常没有 Ghostty 程序：

```bash
ghostty +version
ghostty +list-keybinds --default
ghostty +list-keybinds
ghostty +show-config --default --docs
ghostty +list-fonts
ghostty +list-themes
```

`--default` 用来查看默认绑定，不带该参数用于检查加载个人配置后的绑定。如果提示 `ghostty: command not found`，标准应用安装位置下可以改用：

```bash
/Applications/Ghostty.app/Contents/MacOS/ghostty +list-keybinds --default
```

忘记某个操作时先打开 `⌘ ⇧ P` 命令面板，或查看顶部菜单中的快捷键提示。键位与系统快捷键冲突时，再在配置里单独改绑定。

## 参考

- [官方：自定义快捷键与默认绑定查询](https://ghostty.org/docs/config/keybind)
- [官方：快捷键动作及参数](https://ghostty.org/docs/config/keybind/reference)
- [官方源码：默认键位定义（main，会随版本变化）](https://github.com/ghostty-org/ghostty/blob/main/src/config/Config.zig)
- [官方：配置与重载](https://ghostty.org/docs/config)
- [官方：配置选项参考](https://ghostty.org/docs/config/reference)
- [官方：Shell Integration](https://ghostty.org/docs/features/shell-integration)

相关：[[Ghostty SSH 终端类型报错修复]]、[[macOS 高效开发快捷键指南]]。
