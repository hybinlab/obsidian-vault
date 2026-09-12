---
tags:
  - macos
---
# macOS 开发环境配置文档

## 前置依赖

### Homebrew

macOS 包管理器，以下大多数工具依赖它。

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Xcode Command Line Tools

提供编译器、链接器、系统库头文件，是 C / Rust / 其他原生编译的基础依赖。

```bash
xcode-select --install
```

验证：

```bash
clang --version
```


---

## Python — uv

不要动系统自带的 `/usr/bin/python3`，用 uv 管理 Python 版本和虚拟环境。

### 安装

```bash
brew install uv
```

### 常用命令

```bash
uv python install 3.12       # 安装指定版本
uv python list               # 查看可用版本
uv venv                      # 在当前项目创建虚拟环境
uv venv --python 3.12        # 指定版本创建虚拟环境
source .venv/bin/activate    # 激活虚拟环境
uv add requests              # 安装依赖包
```


---

## Java — SDKMAN

同时管理 JDK 版本和 JVM 生态工具（Gradle、Maven、Kotlin 等）。

### 安装

SDKMAN 安装脚本要求 Bash 4+，macOS 自带 Bash 3.2，需先装新版：

```bash
brew install bash
curl -s "https://get.sdkman.io" | /opt/homebrew/bin/bash
```

装完激活：

```bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
```

> SDKMAN 已自动写入 `~/.zshrc`，新开终端后无需手动 source。

### 安装 JDK

```bash
sdk list java                  # 查看可用版本
sdk install java 21.0.7-tem    # 推荐 Temurin 21（LTS）
```

### 常用命令

```bash
sdk list                       # 查看所有支持的工具
sdk install gradle 8.7         # 安装其他工具
sdk use java 21.0.7-tem        # 当前终端临时切换版本
sdk default java 21.0.7-tem    # 设为全局默认版本
sdk current                    # 查看当前所有工具版本
sdk upgrade java               # 升级到最新稳定版
sdk uninstall java 21.0.7-tem  # 卸载指定版本
sdk selfupdate                 # 更新 SDKMAN 本身
```

### 项目级版本锁定

```bash
sdk env init       # 在项目根目录生成 .sdkmanrc
sdk env install    # 按 .sdkmanrc 安装所需版本
sdk env            # 切换到 .sdkmanrc 指定版本
sdk env clear      # 恢复全局默认版本
```

`.sdkmanrc` 示例：

```
java=21.0.7-tem
gradle=8.7
```

### 常用 JDK 发行版

| 标识 | 发行版 | 说明 |
|----|----|----|
| `-tem` | Temurin（Eclipse） | 推荐，社区主流 LTS |
| `-graalce` | GraalVM CE | 支持 native-image |
| `-amzn` | Corretto（Amazon） | AWS 场景常用 |
| `-zulu` | Zulu（Azul） | 商业支持版本 |


---

## Node.js — nvm

### 安装

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
```

### 常用命令

```bash
nvm install --lts            # 安装最新 LTS
nvm install 20               # 安装指定版本
nvm use 20                   # 切换版本（当前终端）
nvm alias default 20         # 设为默认版本
nvm list                     # 查看已安装版本
```

> 如果系统同时存在 Homebrew 安装的 Node（如 gemini-cli 依赖），两者并存不影响使用，`which node` 应指向 `~/.nvm/versions/node/...`。


---

## Rust — rustup

Rust 官方工具链管理器，无替代方案。

### 安装

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

### 常用命令

```bash
rustup update                # 更新 Rust 工具链
rustup default stable        # 切换到稳定版
rustup default nightly       # 切换到 nightly
rustup target add wasm32-unknown-unknown  # 添加编译目标（如 Tauri/WASM）
rustc --version
cargo --version
```


---

## Go — 官方 Toolchain

Go 1.21+ 支持在 `go.mod` 中声明 `toolchain`，Go 会自动下载对应版本，无需第三方版本管理器。

### 安装

```bash
brew install go
go version
```

### 项目级版本声明

在 `go.mod` 中指定：

```
go 1.24.0
toolchain go1.25.1
```

执行 `go build` 时 Go 会自动拉取所需工具链。


---

## 环境验证

全部装好后统一验证：

```bash
clang --version
uv --version
sdk version
node --version
rustc --version
cargo --version
go version
```


---

## 工具链汇总

| 语言 | 版本管理 | 备注 |
|----|----|----|
| C | Xcode CLT | 系统级依赖，无需版本管理 |
| Python | uv | 同时管理版本和虚拟环境 |
| Java | SDKMAN | 覆盖整个 JVM 生态 |
| Node.js | nvm | 与系统 Node 并存无冲突 |
| Rust | rustup | 官方唯一方案 |
| Go | 官方 Toolchain | 1.21+ 已内置版本管理 |