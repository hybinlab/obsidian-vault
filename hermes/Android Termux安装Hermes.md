---
publish: true
---
## Android / Termux

通过 [Termux](https://termux.dev/) 在 Android 手机上直接运行 Hermes Agent 的测试路径。

提供可用的手机本地 CLI，以及目前已知能在 Android 上干净安装的核心扩展。

### 测试路径支持的功能

测试通过的 Termux 捆绑包包含：

* Hermes CLI
* cron 支持
* PTY/后台终端支持
* Telegram gateway 支持（手动/尽力而为的后台运行）
* MCP 支持
* Honcho memory 支持
* ACP 支持

对应安装命令：

``` bash
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

### 尚未纳入测试路径的功能

以下功能仍需桌面/服务器风格的依赖，或尚未在手机上验证：

* `.[all]` 在 Android 上不支持
* `voice` 扩展被 `faster-whisper -> ctranslate2` 阻塞，ctranslate2 不发布 Android wheel
* 自动 browser / Playwright 引导在 Termux 安装程序中跳过
* Docker 风格的终端隔离在 Termux 内不可用
* Android 仍可能挂起 Termux 后台作业，因此 gateway 持久化为尽力而为而非正常托管服务

### 方式一：一行安装脚本

``` bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

在 Termux 上，安装程序自动使用 pkg 创建 venv，优先尝试 `.[termux-all]` 再回退，跳过未测试的 browser/WhatsApp 引导，并将 hermes 链接到 `$PREFIX/bin`。

### 方式二：手动安装

#### 1. 更新 Termux 并安装系统包

``` bash
pkg update
pkg install -y git python clang rust make pkg-config libffi openssl nodejs ripgrep ffmpeg
```

#### 2. 克隆 Hermes

``` bash
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
```

若已有克隆但无子模块：

``` bash
git submodule update --init --recursive
```

#### 3. 创建虚拟环境

``` bash
python -m venv venv
source venv/bin/activate
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"
python -m pip install --upgrade pip setuptools wheel
```

`ANDROID_API_LEVEL` 对 Rust / maturin 类包（如 `jiter`）很重要。

#### 4. 安装测试通过的 Termux 捆绑包

``` bash
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

如只需最小核心：

``` bash
python -m pip install -e '.' -c constraints-termux.txt
```

#### 5. 将 hermes 加入 Termux PATH

``` bash
ln -sf "$PWD/venv/bin/hermes" "$PREFIX/bin/hermes"
```

#### 6. 验证安装

``` bash
hermes version
hermes doctor
```

#### 7. 启动 Hermes

``` bash
hermes
```

### 推荐后续配置

配置模型：

``` bash
hermes model
```

或在 `~/.hermes/.env` 中直接设置密钥。

重新运行完整设置向导：

``` bash
hermes setup
```

手动安装可选 Node 依赖（browser 工具在 Android 上为实验性）：

``` bash
pkg install nodejs-lts
npm install
```

### 故障排除

**安装** `**.\[all\]**` **报 No solution found：** 使用测试通过的 Termux 捆绑包：

``` bash
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

**uv pip install 在 Android 失败：** 使用 stdlib venv + pip：

``` bash
python -m venv venv
source venv/bin/activate
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

**jiter/maturin 报 ANDROID_API_LEVEL 错误：**

``` bash
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"
python -m pip install -e '.[termux]' -c constraints-termux.txt
```

**hermes doctor 提示 ripgrep 或 Node 缺失：**

``` bash
pkg install ripgrep nodejs
```

**编译 Python 包时构建失败：**

``` bash
pkg install clang rust make pkg-config libffi openssl
```

然后重试安装命令。

### Android 上的已知限制

* Docker 后端不可用
* faster-whisper 本地语音转录不可用
* browser 自动化设置有意被跳过
* 只有 `.[termux]` 和 `.[termux-all]` 为测试通过的 Android 捆绑包

### 相关信息

* [安装指南](/docs/zh-Hans/getting-started/installation)
* [快速开始](/docs/zh-Hans/getting-started/quickstart)