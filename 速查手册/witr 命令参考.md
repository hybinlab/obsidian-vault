# witr 命令参考

> **witr** — "Why is this running?" 进程溯源工具 回答：这个进程为什么在跑、怎么启动的、谁在管它。


---

## 安装（homelab / Linux）

```bash
# 官方安装脚本（自动识别系统架构，推荐）
curl -fsSL https://raw.githubusercontent.com/pranshuparmar/witr/main/install.sh | bash

# apt（Ubuntu 26.04+ / Debian sid+ 及衍生发行版，如 Kali）
sudo apt install witr

# 手动下载二进制（脚本失败时用）
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
curl -fsSL "https://github.com/pranshuparmar/witr/releases/latest/download/witr-${OS}-${ARCH}" -o witr
chmod +x witr && sudo mv witr /usr/local/bin/witr
```

> 也支持 macOS/Windows/FreeBSD 及 Homebrew/Conda/AUR/Winget/npm 等包管理器，见 [Repology](https://repology.org/project/witr/versions)——这里只记 homelab 服务器上实际用的 Linux 安装方式。


---

## 基本用法

```bash
witr <name>          # 按进程名查询（模糊匹配）
witr -i              # 启动 TUI 交互界面（无参数时也会自动进入）
witr --version       # 查看版本
```


---

## 查询方式

```bash
# 按名称（默认模糊匹配）
witr nginx
witr node

# 按名称（精确匹配）
witr nginx --exact
witr nginx -x

# 按 PID
witr --pid 1234
witr -p 1234

# 按端口
witr --port 8080
witr -o 8080

# 按文件（查询持有该文件的进程）
witr --file /var/lib/dpkg/lock
witr -f /var/lib/dpkg/lock

# 按容器名/镜像名（支持 Docker、Podman、K8s 等）
witr --container redis
witr -c redis

# 混合多个目标
witr nginx --port 5432 --pid 1234
witr --port 8080 --port 3306
```


---

## 输出模式

```bash
# 默认输出（完整信息）
witr nginx

# 只显示启动链（单行）
witr nginx --short
witr --port 5000 --short

# 树形显示进程父子关系
witr nginx --tree
witr --pid 1234 --tree

# 显示环境变量
witr nginx --env

# JSON 格式输出
witr nginx --json

# 只显示警告信息
witr nginx --warnings

# 详细模式（含挂载、网络、compose 元数据等）
witr --container redis --verbose
```


---

## 常用组合

```bash
# 查端口被哪个进程占用
witr --port 8080

# 快速看进程启动链
witr nginx --short

# 排查容器详情
witr --container my-app --verbose

# 查某文件被谁持有
witr --file /tmp/app.lock

# 脚本中判断进程是否在运行
witr nginx --short
echo $?   # 0=正常 1=有警告 2=未找到 3=权限不足 4=输入有误 5=内部错误
```


---

## 退出码

| 代码 | 含义 |
|----|----|
| 0 | 找到进程，无警告 |
| 1 | 找到进程，但有警告 |
| 2 | 未找到匹配进程 |
| 3 | 权限不足 |
| 4 | 参数错误或匹配结果不唯一 |
| 5 | 内部错误（未预期的失败） |


---

## TUI 交互界面

```bash
witr       # 无参数直接进入 TUI
witr -i    # 显式指定
```

| Tab | 内容 |
|----|----|
| Processes | 所有进程列表，含进程树面板 |
| Ports | 监听端口及对应进程 |
| Containers | 所有运行中容器（Docker/Podman/K8s 等） |
| Locks | 系统文件锁 |

TUI 快捷键：

| 按键 | 功能 |
|----|----|
| `a` | Ports/Locks Tab 中切换显示全部 |
| `/` | 搜索过滤 |
| 鼠标点击 | 导航、排序、选中行 |


---

## 全部参数速查

| 参数 | 简写 | 说明 |
|----|----|----|
| `--pid` | `-p` | 按 PID 查询（可重复） |
| `--port` | `-o` | 按端口查询（可重复） |
| `--file` | `-f` | 按文件查询（可重复） |
| `--container` | `-c` | 按容器查询（可重复） |
| `--exact` | `-x` | 精确名称匹配 |
| `--short` | `-s` | 只显示启动链 |
| `--tree` | `-t` | 树形显示启动链 |
| `--env` |    | 显示环境变量 |
| `--verbose` |    | 详细输出 |
| `--json` |    | JSON 格式输出 |
| `--warnings` |    | 只显示警告 |
| `--no-color` |    | 禁用颜色 |
| `--interactive` | `-i` | 启动 TUI |
| `--version` | `-v` | 显示版本 |
| `--help` | `-h` | 显示帮助 |


---

## Shell 补全

```bash
# Bash
echo 'eval "$(witr completion bash)"' >> ~/.bashrc && source ~/.bashrc

# Zsh
echo 'eval "$(witr completion zsh)"' >> ~/.zshrc && source ~/.zshrc

# Fish
witr completion fish > ~/.config/fish/completions/witr.fish
```


---

## 卸载

```bash
sudo rm -f /usr/local/bin/witr
sudo rm -f /usr/local/share/man/man1/witr.1
```