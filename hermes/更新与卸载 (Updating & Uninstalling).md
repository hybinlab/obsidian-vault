---
publish: true
---
## 更新

### Git 安装

一行命令更新到最新版本：

``` bash
hermes update
```

这会拉取 `main` 分支最新代码，更新依赖，并提示配置新增的选项。

### pip 安装

PyPI 版本跟踪**标记版本**（主版本和次版本），而非 `main` 上的每次提交。检查并升级：

``` bash
hermes update --check
hermes update
```

或手动：

``` bash
pip install --upgrade hermes-agent
```

> `hermes update` 自动检测新配置选项并提示添加。若跳过了提示，可手动运行 `hermes config check` 查看缺失选项，再用 `hermes config migrate` 交互式添加。

### Git 安装时更新发生了什么

运行 `hermes update` 时依次执行：


1. **配对数据快照** — 轻量级更新前状态快照（涵盖 `~/.hermes/pairing/`、飞书评论规则等运行时修改的状态文件）
2. **Git pull** — 拉取 `main` 分支最新代码并更新子模块
3. **依赖安装** — 运行 `uv pip install -e ".[all]"` 拉取新或变更的依赖
4. **配置迁移** — 检测自当前版本以来的新配置选项并提示设置
5. **Gateway 自动重启** — 更新完成后刷新运行中的 gateway 使新代码立即生效

### 预览模式：hermes update --check

在拉取前想知道是否有更新？运行 `hermes update --check` — git 安装比较与 `origin/main` 的提交差异，pip 安装查询 PyPI 最新版本。不修改任何文件，不重启 gateway。

### 完整更新前备份：--backup

对于高价值 profile，可选择对 `HERMES_HOME` 进行完整预拉取备份：

``` bash
hermes update --backup
```

或设为默认行为（在 `~/.hermes/config.yaml` 中）：

``` yaml
updates:
  pre_update_backup: true
```

更新输出示例：

```
$ hermes update
📥 Pulling latest code...
📦 Updating dependencies...
🔍 Checking for new config options...
🔄 Restarting gateways...
✅ Hermes Agent updated successfully!
```

### 推荐更新后验证

``` bash
git status --short
hermes doctor
hermes --version
```

若使用 gateway：`hermes gateway status`

### 终端在更新中断开

`hermes update` 忽略 SIGHUP，关闭 SSH 会话不会在安装中途杀死它。所有输出镜像到 `~/.hermes/logs/update.log`。

``` bash
tail -f ~/.hermes/logs/update.log
```

**不再需要用 screen 或 tmux 包裹** `**hermes update**`**。**

### 通过消息平台更新

在 Telegram、Discord、Slack、WhatsApp 或 Teams 中发送 `/update`，Bot 短暂离线（5-15 秒）后恢复。

### 手动更新

``` bash
cd /path/to/hermes-agent
export VIRTUAL_ENV="$(pwd)/venv"
git pull origin main
uv pip install -e ".[all]"
hermes config check
hermes config migrate
```

## 回滚

回滚到先前版本：

``` bash
cd /path/to/hermes-agent
git log --oneline -10
git checkout <commit-hash>
git submodule update --init --recursive
uv pip install -e ".[all]"
hermes gateway restart
```

回滚到特定发布标签：

``` bash
git checkout v0.6.0
git submodule update --init --recursive
uv pip install -e ".[all]"
```

> 回滚后运行 `hermes config check`，若遇错误从 config.yaml 中移除无法识别的选项。

### Nix 用户

``` bash
nix flake update hermes-agent
nix profile upgrade hermes-agent
nix profile rollback
```

## 卸载

### Git 安装

``` bash
hermes uninstall
```

卸载程序提供保留配置文件的选项。

### pip 安装

``` bash
pip uninstall hermes-agent
rm -rf ~/.hermes
```

### 手动卸载

``` bash
rm -f ~/.local/bin/hermes
rm -rf /path/to/hermes-agent
rm -rf ~/.hermes
```

> 若将 gateway 安装为系统服务，先停止并禁用：

``` bash
hermes gateway stop
# Linux: systemctl --user disable hermes-gateway
# macOS: launchctl remove ai.hermes.gateway
```

## 相关信息

* [安装指南](/docs/zh-Hans/getting-started/installation)
* [快速开始](/docs/zh-Hans/getting-started/quickstart)
* [Nix & NixOS Setup](/docs/zh-Hans/getting-started/nix-setup)