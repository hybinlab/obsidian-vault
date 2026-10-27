---
publish: true
tags:
  - 命令笔记
---

## fnm（Fast Node Manager）

fnm 是 Node.js 官方推荐的版本管理器，基于 Rust，性能比 nvm 快。

> 安装脚本：`curl -o- https://fnm.vercel.app/install | bash`  
> 默认安装路径：`~/.local/share/fnm/`（遵循 XDG Base Directory 规范）

### 核心命令

| 命令                        | 说明                         |
| ------------------------- | -------------------------- |
| `fnm install <version>`   | 安装指定版本（如 `fnm install 22`） |
| `fnm use <version>`       | 切换到指定版本                    |
| `fnm default <version>`   | 设为默认版本                     |
| `fnm ls`                  | 列出已安装版本                    |
| `fnm ls-remote`           | 列出远程可用版本                   |
| `fnm current`             | 显示当前激活版本                   |
| `fnm uninstall <version>` | 卸载指定版本                     |

### 跨大版本升级

```bash
fnm install 24     # 安装新版
fnm use 24         # 切换
fnm default 24     # 设为默认
fnm uninstall 22   # 旧版本不会自动删除，手动清理
```

### 验证

```bash
node -v   # Node.js 版本
npm -v    # npm 版本
```

---

## nvm（Node Version Manager）

nvm 是最流行的 Node.js 版本管理器，通过 shell 脚本实现。

> 安装：`curl -o- https://install.sh | bash`（需先安装 git）

### 核心命令

| 命令 | 说明 |
|---|---|
| `nvm install <version>` | 安装指定版本（如 `nvm install 22`） |
| `nvm use <version>` | 切换到指定版本 |
| `nvm alias default <version>` | 设为默认版本 |
| `nvm ls` | 列出已安装版本 |
| `nvm ls-remote` | 列出远程可用版本 |
| `nvm current` | 显示当前版本 |
| `nvm uninstall <version>` | 卸载指定版本 |

### 常用示例

```bash
nvm install --lts      # 安装最新 LTS 版
nvm install 22        # 安装 22.x 最新补丁版
nvm use 22            # 切换到 22
nvm alias default 22   # 永久设为默认
```

### 更多操作

| 命令 | 说明 |
|---|---|
| `nvm version` | 显示 nvm 自身版本 |
| `nvm ls-remote --lts` | 列出所有 LTS 版本 |
| `nvm cache` | 显示缓存目录 |
| `nvm deactivate` | 取消当前 shell 的 nvm 环境 |
| `nvm uninstall <version>` | 卸载指定版本 |

---

## fnm vs nvm 对比

| 维度 | fnm | nvm |
|---|---|---|
| 性能 | 快（Rust） | 较慢（shell 脚本） |
| 官方推荐 | 是 | 否 |
| 安装路径 | `~/.local/share/fnm/` | `~/.nvm/` |
| 跨平台 | macOS/Linux/Windows | macOS/Linux（Windows 需用 nvm-windows） |
| .nvmrc 支持 | ✅ | ✅ |

两者都支持 `.nvmrc` / `.node-version` 文件，在项目目录下直接 `fnm use` / `nvm use` 自动读取文件中的版本号。

---

## 相关笔记

- [[homelab/初始化环境/nodejs安装]] — LXC 场景下 fnm 和 NodeSource 的实际选型记录
- [[ansible/踩坑记录/Docker & fnm 部署踩坑记录]] — fnm 安装路径踩坑实录
