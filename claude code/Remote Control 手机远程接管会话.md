---
publish: true
tags:
  - claude-code
  - remote-control
  - tmux
---

> 目标：在服务器上开一个 Claude Code 会话，**关掉电脑终端 / SSH 断开后**，继续在手机上和它对话、审批权限、把任务做完。
> 来源：官方文档 <https://code.claude.com/docs/en/remote-control>。

相关：[[Claude Code 官方文档导读]]、[[自动化与并行]]、[[最佳实践]]

## 原理

- **Remote Control** 让本机上运行的 Claude Code 进程连到 claude.ai，然后就能在 `claude.ai/code` 或 **Claude 手机 App** 里看到这个会话并接着对话。
- 代码、文件、命令**仍然在本机执行**，手机只是个遥控器。
- 关键在于：**本机的 `claude` 进程必须一直活着**。官方原话：关掉终端、或者 `claude` 进程停止后，会话就会下线；如果是 SSH 到远程机器，要在 `tmux` 或 `screen` 里启动。

## 前置条件

- Pro / Max / Team / Enterprise 订阅，用 `/login` 登录 claude.ai 账号（**不支持 API key**）。手机 App 登录**同一个账号**。
- 不能设置 `ANTHROPIC_BASE_URL` 指向网关或代理，也不能设置 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`。
- 目标目录需要被信任过：先在这个目录直接跑一次 `claude` 并确认信任。（没有终端可交互时，会报 `Workspace not trusted` 并退出。）
- 第一次使用会询问 `Enable Remote Control? (y/n)`，确认一次即可。
- 机器保持开机、联网。

## 三种开启方式

| 方式 | 命令 | 特点 |
| --- | --- | --- |
| 服务模式 | `claude remote-control --name homelab` | 常驻进程，可以同时服务多个会话（默认最多 32 个），手机上还能开新会话；按空格显示二维码 |
| 交互会话 | `claude --remote-control homelab`（或 `--rc`） | 正常的终端会话，同时手机也能操作 |
| **已有会话中途开启** | 在会话里输入 `/remote-control`（或 `/rc`） | **保留当前对话历史**，最适合"聊到一半要出门"的场景 |

服务模式的常用参数：

| 参数 | 作用 |
| --- | --- |
| `--name <名字>` | 会话名，显示在 claude.ai/code 和 App 里 |
| `--permission-mode <mode>` | 会话的初始权限模式，如 `acceptEdits` |
| `--spawn worktree` | 每个新会话用独立的 git worktree（需要 git 仓库）；运行中按 `w` 切换 |
| `--spawn session` | 单会话模式，只服务一个会话 |
| `-c` / `--continue` | 找回这个目录上一次服务的会话（停止后约 4 小时内有效） |
| `--session-id <id>` | 找回指定会话 |

想让每个交互会话都自动开启：`/config` 里打开 **Enable Remote Control for all sessions**，或者在 `~/.claude/settings.json` 里设置 `"remoteControlAtStartup": true`。

## 操作步骤

### 方案 A：从零开始（tmux + 服务模式）

```bash
ssh root@<服务器IP>
tmux new -s cc                    # 已存在就用 tmux attach -t cc
cd /path/to/project
claude remote-control --name homelab
# 按 Ctrl-b 再按 d 脱离 tmux → 可以关终端了
```

### 方案 B：正在聊的会话，要出门了

前提：这个会话本来就是**在 tmux 里**开的。

1. 在会话里输入 `/rc`，对话历史会一起带过去；
2. 按 `Ctrl-b` 再按 `d` 脱离 tmux，关掉终端。

> 如果当前会话**不在** tmux 里，关掉终端它就没了。可以先 `/rc` 让手机接上，但电脑终端不能关；或者退出后在 tmux 里用 `claude --continue --remote-control` 接回这个对话再开启。

### 方案 C：让 Claude 代为启动

自己不方便开终端时，可以让当前会话里的 Claude 通过 Bash 起一个后台 tmux：

```bash
tmux new -d -s cc -c /path/to/project 'claude remote-control --name homelab'
tmux capture-pane -pt cc | tail -20     # 确认已经连上
```

注意：这是一个**全新的会话**，看不到原来对话的内容；不用的时候记得 `tmux kill-session -t cc`。

### 在手机上继续

- 打开 Claude App，点底部导航的 **Code**，找到对应名字的会话。在线的会话显示一个电脑图标加**绿点**。
- 也可以扫终端显示的二维码，或在浏览器打开会话 URL。
- 权限确认和 Claude 的提问都会转到手机上，会一直等你回答。
- 还没装 App 的话，在 Claude Code 里运行 `/mobile` 显示下载二维码。

### 回到电脑

```bash
tmux attach -t cc
```

## 手机推送通知

1. 手机安装 Claude App，用同一账号登录，允许通知；
2. 终端里 `/config`，开启 **Push when Claude decides**（任务完成等）和/或 **Push when actions required**（权限确认、提问）。

提示词里也可以直接说 "notify me when the tests finish"。如果 `/config` 显示 **No mobile registered**，打开一次手机 App 刷新推送 token 即可。

## 手机上能用的命令

- 可以用：`/compact`、`/clear`、`/context`、`/usage`、`/recap`、`/exit`；`/model sonnet`、`/effort high`、`/fast`、`/rename`（需要带参数）；`/mcp`（返回文字摘要）；`/config key=value`。
- 只能在本地终端用：`/plugin`、`/resume` 等需要终端界面的命令。

## 常见问题

- **手机上看不到会话**：`tmux ls` 确认进程还活着，attach 进去看有没有报错；确认两边是同一个账号。
- **任务卡住不动**：大概率在等权限确认，到手机上看一眼，或者打开推送通知。长任务可以用 `--permission-mode acceptEdits` 或 auto 模式减少打断，但要清楚其中的风险。
- **服务模式的进程被 Ctrl+C 停了**：约 4 小时内在同一目录运行 `claude remote-control`（找回所有会话）或 `claude remote-control -c` / `--session-id <id>`（找回单个）。
- **`--rc` 或 `/rc` 开的会话退出了**：用 `claude --continue` 或 `claude --resume` 恢复对话。
- **断网**：服务模式大约 10 分钟后放弃并退出，需要重新启动；交互会话会一直重试，网络恢复后自动重连。
- **机器重启**：tmux 会话会丢，需要重新执行上面的步骤。

## 速查

```bash
tmux new -s cc
cd /path/to/project
claude remote-control --name <会话名>      # 或在已有会话里输入 /rc
# 按 Ctrl-b d 脱离 → 关终端 → 在手机 App 的 Code 里继续
tmux attach -t cc                          # 回来
```
