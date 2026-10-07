---
publish: true
---
两分钟内通过一行命令完成 Hermes Agent 的安装。

## 快速安装

### Linux / macOS / WSL2

一行命令完成安装，跟踪 `main` 分支获取最新变更：

``` bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### Windows 原生 (PowerShell) — 早期 Beta

原生 Windows 支持处于**早期 Beta** 阶段。请优先考虑在 **WSL2** 中运行 Linux/macOS 一行命令安装。

PowerShell 中运行：

``` powershell
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
```

安装程序自动处理全部依赖：uv、Python 3.11、Node.js 22、ripgrep、ffmpeg，以及**便携式 Git Bash** (PortableGit)。仓库克隆至 `%LOCALAPPDATA%\hermes\hermes-agent`，创建虚拟环境，并将 `hermes` 添加至 User PATH。安装后重启终端使 PATH 生效。

**Git 处理方式：**

* 若系统已有 git，直接使用现有安装
* 若无，则下载 PortableGit (\~50MB) 至 `%LOCALAPPDATA%\hermes\git`，完全隔离，不影响系统原有 Git
* 32 位 Windows 回退至 MinGit（缺少 bash，terminal-tool / agent-browser 功能不可用）

**为什么不用 winget：** winget 在系统 Git 处于损坏状态时会彻底失败。便携 Git 方案完全绕过注册表和 winget，彻底损坏时只需 `Remove-Item %LOCALAPPDATA%\hermes\git` 重新运行即可。

安装程序同时设置 `HERMES_GIT_BASH_PATH` 环境变量指向 `bash.exe`。

原生 Windows 和 WSL2 可以共存：原生数据在 `%LOCALAPPDATA%\hermes`，WSL 数据在 `~/.hermes`。

### Android / Termux

``` bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

自动检测 Termux 并切换至 Android 流程：

* 使用 Termux `pkg` 安装系统依赖 (git, python, nodejs, ripgrep, ffmpeg, build tools)
* 使用 `python -m venv` 创建虚拟环境
* 自动设置 `ANDROID_API_LEVEL` 用于 Android wheel 编译
* 优先安装 `.[termux-all]`，失败时回退至 `.[termux]`，最终回退至基础安装
* 默认跳过未测试的 browser / WhatsApp 引导

### Windows 功能支持现状 (早期 Beta)

除基于浏览器的前端面板外，其余全部原生运行：

| 功能 | Windows 原生 | 备注 |
|----|----|----|
| CLI (hermes chat, setup, gateway 等) | ✓ | 使用系统默认终端 |
| Gateway (Telegram, Discord, Slack 等) | ✓ | 作为后台 PowerShell 进程运行 |
| Cron 调度器 | ✓ | 原生 |
| Browser 工具 | ✓ | 通过 Node.js Chromium |
| MCP 服务 | ✓ | stdio 和 HTTP 传输均支持 |
| Dashboard /chat 终端面板 | ✗ | 仅 WSL2 支持（需要 POSIX PTY） |

如遇编码相关 bug，设置 `HERMES_DISABLE_WINDOWS_UTF8=1` 回退至 cp1252 模式。

## 安装程序做了什么

自动处理所有依赖：Python、Node.js、ripgrep、ffmpeg，克隆仓库，创建虚拟环境，配置全局 `hermes` 命令，以及 LLM provider 配置。

### 安装布局

| 安装方式 | 代码位置 | hermes 二进制 | 数据目录 |
|----|----|----|----|
| pip install | Python site-packages | \~/.local/bin/hermes | \~/.hermes/ |
| Per-user (git) | \~/.hermes/hermes-agent/ | \~/.local/bin/hermes (symlink) | \~/.hermes/ |
| Root-mode (sudo) | /usr/local/lib/hermes-agent/ | /usr/local/bin/hermes | /root/.hermes/ |

Root 模式采用 FHS 标准布局 (`/usr/local/lib/...`, `/usr/local/bin/hermes`)，适合多用户共享部署。

## 安装后配置

重载 shell 后即可开始对话：

``` bash
source ~/.bashrc   # 或: source ~/.zshrc
hermes             # 启动对话！
```

后续可通过以下命令重新配置各项设置：

``` bash
hermes model          # 选择 LLM provider 和模型
hermes tools          # 配置启用的工具
hermes gateway setup  # 设置消息平台
hermes config set     # 设置单个配置值
hermes setup          # 运行完整设置向导一次性配置所有内容
```

## 前置要求

**pip install：** 仅需 Python 3.11+，其他全部自动处理。

**Git 安装：** 唯一前置要求是 Git，其余全部自动处理（uv、Python 3.11、Node.js v22、ripgrep、ffmpeg）。

> 无需手动安装 Python、Node.js、ripgrep 或 ffmpeg。安装程序自动检测并安装缺失的依赖。确认 `git --version` 可用即可。

## Nix 用户

Nix/NixOS 用户请参考 [Nix & NixOS Setup](/docs/zh-Hans/getting-started/nix-setup) 页面，使用 Nix flake、声明式 NixOS 模块和可选容器模式。

## 手动 / 开发者安装

如需从源码克隆仓库安装（用于贡献代码、跟踪特定分支或完全控制虚拟环境），请参考 Contributing 指南中的 [Development Setup](https://hermes-agent.nousresearch.com/docs/zh-Hans/contributing/development#development-setup) 部分。

## 非 sudo / 系统服务用户安装

以非特权用户运行 Hermes（如 systemd service account）完全支持。唯一需要 root 的是 Playwright 的 `--with-deps` 步骤（安装 libnss3、libxkbcommon 等 Chromium 依赖库）。安装程序会检测 sudo 是否可用并优雅降级——将 Chromium 安装至该服务用户的本地 Playwright 缓存，并打印管理员需要单独运行的命令。

**推荐做法 (Debian/Ubuntu)：**

以有 sudo 权限的管理员用户一次性安装 Chromium 依赖：

``` bash
sudo npx playwright install-deps chromium
```

然后以非特权服务用户身份运行常规安装程序即可。

## 相关信息

* [快速开始 (Quickstart)](/docs/zh-Hans/getting-started/quickstart)
* [更新与卸载](/docs/zh-Hans/getting-started/updating)
* [Nix & NixOS Setup](/docs/zh-Hans/getting-started/nix-setup)