---
publish: true
---
> 适用环境：Ubuntu Server，OpenClaw 已注册为 systemd 用户服务


---

## 前置要求

* Python 3.10+
* Node.js 22+
* OpenClaw 已安装并运行
* 可访问的 OpenAI 兼容 LLM 接口（含 embedding 模型）


---

## 部署步骤

### 1. 创建 Python 虚拟环境

```bash
sudo apt install python3.12-venv -y
python3 -m venv ~/.venv/openviking
source ~/.venv/openviking/bin/activate
```

> ⚠️ Ubuntu/Debian 系统直接 `python3 -m venv` 会报 ensurepip 不可用，需先装 `python3.12-venv`。


---

### 2. 安装 OpenViking

```bash
pip install openviking -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> ⚠️ 直连 PyPI 容易超时，建议加 `-i` 换清华镜像源。

验证：

```bash
openviking-server --version
```


---

### 3. 创建配置文件

```bash
mkdir -p ~/.openviking
cat > ~/.openviking/ov.conf << 'EOF'
{
  "storage": {
    "workspace": "/home/openclaw/openviking_workspace"
  },
  "embedding": {
    "dense": {
      "api_base": "https://你的供应商地址/v1",
      "api_key": "你的key",
      "provider": "openai",
      "dimension": 1024,
      "model": "bge-m3"
    }
  },
  "vlm": {
    "api_base": "https://你的供应商地址/v1",
    "api_key": "你的key",
    "provider": "openai",
    "model": "你的chat模型名"
  }
}
EOF
```

**Embedding 模型维度对照：**

| 模型 | 维度 |
|----|----|
| `bge-m3` / `BAAI/bge-m3` | 1024 |
| `Qwen3-Embedding-8B` | 4096 |
| `bge-multilingual-gemma2` | 3584 |


---

### 4. 测试 OpenViking 服务

```bash
openviking-server
```

新开终端验证：

```bash
source ~/.venv/openviking/bin/activate
ov status
```

看到所有队列和 vikingdb 状态为 healthy 即正常，`Ctrl+C` 停止。


---

### 5. 安装 OpenClaw 插件

```bash
npm install -g openclaw-openviking-setup-helper
ov-install
```

安装过程中的选项：

| 提示 | 填写 |
|----|----|
| Plugin mode | `local` |
| OpenViking workspace path | 直接回车（默认） |
| HTTP port | 直接回车（默认 1933） |
| VLM model | 你的 chat 模型名 |
| Embedding model | `bge-m3` |
| VLM/Embedding API key | 填入 key |


---

### 6. 配置 systemd 服务环境变量

OpenClaw 以 systemd 服务运行时，不会继承 shell 的环境变量，需手动将 `OPENVIKING_PYTHON` 写入服务文件。

找到服务文件位置：

```bash
systemctl --user cat openclaw-gateway.service
# 文件路径一般为 ~/.config/systemd/user/openclaw-gateway.service
```

编辑服务文件，在 `[Service]` 段末尾加一行：

```bash
nano ~/.config/systemd/user/openclaw-gateway.service
```

添加：

```ini
Environment="OPENVIKING_PYTHON=/home/openclaw/.venv/openviking/bin/python3"
```

> ⚠️ 不要用 `systemctl --user edit` 生成的 override 文件方式，直接编辑原始服务文件更可靠。
>
> ⚠️ 不要用 `sed` 替换，容易写入错误格式，用 `nano` 手动编辑。

重载并重启：

```bash
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
```


---

### 7. 信任插件

```bash
openclaw config set plugins.allow '["openviking"]'
systemctl --user restart openclaw-gateway.service
```


---

### 8. 验证

```bash
journalctl --user -u openclaw-gateway.service --no-pager | grep -i openviking | tail -5
```

看到以下两行即成功：

```
openviking: registered context-engine (before_prompt_build=auto-recall, afterTurn=auto-capture)
openviking: local server started (http://127.0.0.1:1933, config: /home/openclaw/.openviking/ov.conf)
```

> 注意：`openclaw status` 的 Memory 行不会显示 openviking，这是正常的。OpenViking Plugin 2.0 使用 context-engine 架构，与旧版 memory 插件显示方式不同。


---

## 常见问题

| 现象                                                  | 原因                                | 解决                                              |
| --------------------------------------------------- | --------------------------------- | ----------------------------------------------- |
| `python3 -m venv` 报 ensurepip 不可用                   | 缺少 venv 包                         | `sudo apt install python3.12-venv`              |
| `pip install` 超时                                    | PyPI 连接慢                          | 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `ModuleNotFoundError: No module named 'openviking'` | systemd 服务用系统 python，找不到 venv 里的包 | 在服务文件加 `Environment="OPENVIKING_PYTHON=..."`    |
| gateway 日志无 `local server started`                  | 环境变量未生效                           | 确认直接编辑了服务文件而非 override，且执行了 `daemon-reload`     |
| `openclaw status` Memory 行不显示 openviking            | Plugin 2.0 架构变化                   | 正常，看 journalctl 日志确认即可                          |