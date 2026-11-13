---
publish: false
tags:
  - homelab
  - orca
  - AI-Agent
---

# Orca 服务端本地部署方案

> **状态：未安装、待部署。** 目标为 agent VM `192.168.31.4`；现有 WireGuard 已可用于手机异地访问。下文安装包版本为编写方案时的示例，执行时需重新核对官方发行版。

## 部署选择

采用 Ubuntu 24.04 x86_64 + 官方 `.deb` + `orca-ide serve`，先通过内网连接。无需为此安装 Docker，也无需从源码构建。Linux 命令名为 `orca-ide`，不要与 GNOME 屏幕阅读器的 `orca` 混淆。

部署位置：

| 主机 | 地址 | 考量 |
| --- | --- | --- |
| agent | 192.168.31.4 | 当前会话所在主机，8G 内存，与 Hermes/Hindsight 共用；先少量会话试用 |

已选定 **agent VM**，计划固定 TCP 6768。客户端通过现有 WireGuard 回家访问 agent，再由 agent 使用 SSH 连接其他 VM。运行账号、CLI 登录和凭据访问范围在实际部署时核对；后文独立 `orca` 用户示例不代表当前已创建或已配置账号。仓库、worktree、终端、Agent 进程及凭据均在服务端；资源消耗取决于并发量与项目构建任务。

## 安装软件包

以下命令在选定的 Ubuntu 服务器上执行。使用具备 sudo 权限的管理员账号；如果当前为 root，可去掉 sudo。

```bash
uname -m
df -h /
free -h
ss -lntp 'sport = :6768'

sudo apt update
sudo apt install -y curl git ca-certificates dbus-user-session

curl -fL --retry 3 \
  https://github.com/stablyai/orca/releases/download/v1.4.252/orca-ide_1.4.252_amd64.deb \
  -o /tmp/orca-ide_1.4.252_amd64.deb

sudo apt install -y /tmp/orca-ide_1.4.252_amd64.deb
command -v orca-ide
```

这组下载命令固定为 amd64 和 v1.4.252。其他架构或后续版本从 Releases 选择对应包，不直接沿用文件名。`.deb` 后续升级需要重新安装新版软件包。

首次创建运行账号（已有合适的普通用户可直接使用该用户，并替换后续用户名）：

```bash
sudo adduser orca
sudo loginctl enable-linger orca
```

然后从电脑通过 SSH 登录这个账号，以建立正常的用户会话。以下地址使用 agent：

```bash
ssh orca@192.168.31.4
```

后续 Orca、账户注册和 `systemctl --user` 命令均在该账号的 SSH 会话内执行。

## 前台试运行

```bash
orca-ide serve --help

orca-ide serve \
  --bind 192.168.31.4 \
  --port 6768 \
  --pairing-address 192.168.31.4 \
  --refuse-public
```

`--bind` 决定监听网卡，`--pairing-address` 只决定配对链接中的地址。上述为桌面客户端连接的试运行示例；手机配对对绑定地址和额外监听的要求，需在实际部署时按当前版本核对。若已有防火墙拦截，只对实际使用的内网客户端来源开放所需端口。

在电脑安装并打开相近版本的 Orca，进入 **Settings → Remote Orca Servers → Add Server**，粘贴服务器终端输出的配对链接，连接后添加一个测试仓库，创建终端并检查命令执行位置。配对链接相当于访问凭据，不放进笔记或公开日志。

这条路径使用 Orca 客户端连接服务端，不是直接在浏览器输入 `http://IP:6768` 的安装方式。

## Agent 账户

先在服务端为运行用户安装、登录准备使用的 Agent CLI；客户端已有的登录不会自动传到服务端。按需在服务端注册托管账户：

```bash
orca-ide account add --agent claude
# 或选择 Codex：
orca-ide account add --agent codex
orca-ide account list
```

只配置实际需要的 Agent。随后在客户端启动一个简单任务，确认 Agent 可用，再测试关闭客户端、重新连接后的会话恢复。

## 开机自启

前台验证成功后先按 Ctrl-C，再使用官方提供的用户级 systemd 服务安装命令。先检查当前安装版本是否提供该命令：

```bash
orca-ide serve service install --help

orca-ide serve service install \
  --bind 192.168.31.4 \
  --port 6768 \
  --pairing-address 192.168.31.4 \
  --refuse-public

orca-ide serve service status
systemctl --user status orca-serve.service --no-pager
journalctl --user -u orca-serve.service -n 100 --no-pager
ss -lntp 'sport = :6768'
```

官方实现会写入用户服务、启用并启动它；默认 profile 的单元名为 `orca-serve.service`。若指定自定义 profile，以命令输出的单元名为准。服务启动不向日志打印配对链接，需要新链接时以相同运行用户执行：

```bash
orca-ide pair --address 192.168.31.4
```

常用维护命令：

```bash
systemctl --user restart orca-serve.service
systemctl --user stop orca-serve.service
orca-ide serve service uninstall
```

卸载用户服务不等于删除工作目录、账户凭据或软件包。

## 内存与远程访问

需要限制每个终端的内存时，给用户服务添加环境变量。例如先按每终端 2G 试用，再根据构建任务调整：

```bash
systemctl --user edit orca-serve.service
```

写入：

```ini
[Service]
Environment=ORCA_TERMINAL_MEMORY_MAX=2G
Environment=ORCA_TERMINAL_MEMORY_SWAP_MAX=0
```

这些限制依赖 systemd、cgroup v2 和 linger，作用于各终端 scope，不是整个 Orca 的总内存上限。环境由终端 host 启动时读取；它可能跨服务重启存活，需在无任务运行时重启服务器等方式让其重新读取。查看日志确认限制是否成功应用。

内网直接连接 agent；异地通过已部署的 WireGuard 访问，不依赖 Tailscale。Orca 端口不通过 FRP 直接暴露到公网。配对方式、Codex 会话及手机连接均待实际部署验收。

## 官方来源

- [Remote Orca Servers](https://github.com/stablyai/orca/blob/main/docs/site/content/docs/remote-servers.mdx)
- [Linux 安装说明](https://github.com/stablyai/orca/blob/main/docs/site/content/docs/install.mdx)
- [v1.4.252 发布及安装包](https://github.com/stablyai/orca/releases/tag/v1.4.252)
- [服务安装实现](https://github.com/stablyai/orca/blob/main/src/cli/handlers/serve-service.ts)
- [systemd 单元生成实现](https://github.com/stablyai/orca/blob/main/src/cli/runtime/serve-service-unit.ts)

文档和源码链接跟随 main，可能领先稳定发行版；执行前以已安装版本的 `--help` 为准。
