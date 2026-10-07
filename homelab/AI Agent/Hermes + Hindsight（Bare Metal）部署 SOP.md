> Hindsight 专项笔记（API 细节、概念）另开在 [[homelab/AI Agent/Hindsight/]] 文件夹，这篇是 Hermes+Hindsight 联合部署的 SOP，两者耦合较深，暂不拆分。

> **适用场景**：Hermes Agent 与 Hindsight API 同机部署在 Agent VM；PostgreSQL 独立部署在 DB VM；Hindsight 使用本地 Embedding / Reranker（中英混合），LLM 使用 MiniMax 国内 API。
> **验证版本**：Hindsight API `v0.10.1` / torch `2.14.0+cpu`
> **验证环境**：PVE 9.2 · Ubuntu 24.04 · Python 3.12 · uv · PostgreSQL 16 · pgvector 0.6.0
> **原则**：文中密码、API Key、IP 均为占位符，真实凭据不进 Git。

---

## 1. 架构

```text
Hermes Agent
    │ http://127.0.0.1:8888（只监听本机）
    ▼
Hindsight API  (/opt/hindsight, systemd)
    ├── LLM ────────► MiniMax-M2.7  https://api.minimaxi.com/v1
    ├── Embedding ──► 本地 BAAI/bge-m3           (dim=1024, CPU)
    ├── Reranker ───► 本地 BAAI/bge-reranker-base (CPU)
    └── PostgreSQL ─► <DB_VM_IP>:5432 / hindsight + pgvector
```

---

## 2. 前置条件

### Agent VM

| 项 | 要求 | 说明 |
|---|---|---|
| 内存 | **≥ 8 GB** | bge-m3 + reranker 常驻约 3.3 GB，2 GB 会 OOM |
| 磁盘 | 根分区可用 ≥ 15 GB | venv ≈ 2 GB（CPU torch），模型缓存 ≈ 6–7 GB |
| Python | ≥ 3.11 | Ubuntu 24.04 自带 3.12 |
| 工具 | `uv`、`postgresql-client` | |
| 网络 | 可达 MiniMax API、DB VM:5432、Hugging Face | |

> PVE 扩磁盘后，VM 内要逐层扩：
> ```bash
> growpart /dev/sda 3
> pvresize /dev/sda3
> lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
> ```
> PVE 改内存后必须在 PVE 里**关机再开机**，VM 内 `reboot` 不会生效（未开热插拔时）。

### DB VM

- PostgreSQL 16，已安装 `postgresql-16-pgvector`

---

## 3. PostgreSQL / pgvector（DB VM）

```bash
apt install -y postgresql-16-pgvector
sudo -u postgres psql <<'SQL'
CREATE USER hindsight WITH PASSWORD '<DB_PASSWORD>';
CREATE DATABASE hindsight OWNER hindsight;
\c hindsight
CREATE EXTENSION IF NOT EXISTS vector;
SQL
```

`pg_hba.conf` 只放行 Agent VM：

```text
host  hindsight  hindsight  <AGENT_VM_IP>/32  scram-sha-256
```

确认 `postgresql.conf` 中 `listen_addresses` 包含内网地址，然后 `systemctl reload postgresql`。

在 Agent VM 验证：

```bash
psql "postgresql://hindsight:<DB_PASSWORD>@<DB_VM_IP>:5432/hindsight" \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"
```

---

## 4. 安装 Hindsight（Agent VM）

```bash
mkdir -p /opt/hindsight/hf-cache
cd /opt/hindsight
uv venv
PY=/opt/hindsight/.venv/bin/python

# 必须带 --torch-backend cpu，否则会装 CUDA 版 torch + nvidia-* 包（venv 6.4 GB → 2 GB 的差距）
uv pip install --python $PY hindsight-api --torch-backend cpu
```

验证：

```bash
uv pip show --python $PY hindsight-api | grep Version
$PY -c "import torch; print(torch.__version__, torch.cuda.is_available())"   # 期望: x.x.x+cpu False
uv pip check --python $PY
du -sh /opt/hindsight/.venv                                                 # 期望: ~2 GB
```

> **如果已经装成了 CUDA 版**，补救：
> ```bash
> uv pip install --python $PY --reinstall torch --index-url https://download.pytorch.org/whl/cpu
> uv pip uninstall --python $PY $(uv pip list --python $PY | awk '/^(nvidia-|triton)/{print $1}')
> uv pip check --python $PY    # 该方式会顺带降级 filelock/fsspec 等，有冲突则: uv pip install --python $PY -U filelock fsspec
> ```

> **注意**：`hindsight-api` 没有 `--version` 参数，查版本用 `uv pip show`。uv 创建的 venv 默认没有 `pip`，一律用 `uv pip --python $PY ...`，避免装进系统 Python。

---

## 5. 环境变量

`/opt/hindsight/hindsight.env`：

```ini
HINDSIGHT_API_DATABASE_URL="postgresql://hindsight:<DB_PASSWORD>@<DB_VM_IP>:5432/hindsight"

HINDSIGHT_API_LLM_PROVIDER="minimax"
HINDSIGHT_API_LLM_MODEL="MiniMax-M2.7"
HINDSIGHT_API_LLM_BASE_URL="https://api.minimaxi.com/v1"
HINDSIGHT_API_LLM_API_KEY="<MINIMAX_API_KEY>"

# 中英混合：多语言 embedding + reranker；维度从模型自动识别（bge-m3 = 1024）
HINDSIGHT_API_EMBEDDINGS_PROVIDER="local"
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL="BAAI/bge-m3"
HINDSIGHT_API_RERANKER_PROVIDER="local"
HINDSIGHT_API_RERANKER_LOCAL_MODEL="BAAI/bge-reranker-base"

HINDSIGHT_API_HOST="127.0.0.1"
HINDSIGHT_API_PORT="8888"

HF_HOME="/opt/hindsight/hf-cache"
```

```bash
chmod 600 /opt/hindsight/hindsight.env
```

> 默认值陷阱：`HINDSIGHT_API_HOST` 不设 = `0.0.0.0`（全 LAN 暴露）；embedding 不设 = `bge-small-en-v1.5`（纯英文，中文召回差）；LLM 不设 = `openai/gpt-4o-mini`；数据库不设 = 内嵌 `pg0`。

---

## 6. 预下载模型（必做）

Hindsight 启动时模型初始化有超时（`HINDSIGHT_API_MODEL_INIT_TIMEOUT`，默认 300s），首次边启动边下载 bge-m3 会超时退出。先单独下载：

```bash
set -a; source /opt/hindsight/hindsight.env; set +a
/opt/hindsight/.venv/bin/hf download BAAI/bge-m3            --exclude "onnx/*"
/opt/hindsight/.venv/bin/hf download BAAI/bge-reranker-base --exclude "onnx/*"
/opt/hindsight/.venv/bin/hf cache scan
```

> 已有缓存在 `/root/.cache/huggingface` 的，直接 `mv /root/.cache/huggingface /opt/hindsight/hf-cache`，设好 `HF_HOME` 即可复用，未完成的文件会断点续传。

---

## 7. Hermes 配置 Hindsight Provider

```bash
hermes memory setup      # 选择 Hindsight
hermes memory status     # 期望: Provider: hindsight / Plugin: installed / Status: available
```

`~/.hermes/hindsight/config.json` 关键项：

```json
{
  "mode": "local_external",
  "api_url": "http://localhost:8888",
  "llm_provider": "minimax",
  "llm_model": "MiniMax-M2.7",
  "bank_id": "hermes",
  "recall_budget": "mid"
}
```

> `Status: available` 只代表插件装好，不代表 API 在跑。`local_external` 模式依赖 `127.0.0.1:8888` 上的 Hindsight 服务。

---

## 8. 手工启动验证

```bash
set -a; source /opt/hindsight/hindsight.env; set +a
env | grep '^HINDSIGHT_API_' | sed -E 's/(API_KEY|DATABASE_URL)=.*/\1=***REDACTED***/'
/opt/hindsight/.venv/bin/hindsight-api --log-level debug
```

### 成功判据（按出现顺序）

```text
Database: postgresql://***:***@<DB_VM_IP>:5432/hindsight      ← 不能是 pg0
LLM: provider=minimax, model=MiniMax-M2.7
Connection verified: minimax/MiniMax-M2.7
Reranker: local provider initialized (device: cpu, ...)
Embeddings: local provider initialized (dim: 1024, device: cpu)
Database migrations completed successfully
Embedding dimension OK for memory_units: 1024                   ← 或首次迁移时的 Altering ... to 1024
PostgreSQL pool created
Application startup complete.
Uvicorn running on http://127.0.0.1:8888
```

正常启动（模型已缓存）约 20 秒。

---

## 9. 冒烟测试（中文检索）

```bash
# 写入（async=false 同步等待 LLM 抽取）
curl -s -X POST http://127.0.0.1:8888/v1/default/banks/test/memories \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"content":"homelab 数据库 VM 地址是 <DB_VM_IP>，运行 PostgreSQL 和 MySQL"}],"async":false}'

# 换一种说法召回
curl -s -X POST http://127.0.0.1:8888/v1/default/banks/test/memories/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"PG 数据库在哪台机器上？"}'
```

能召回上面那条即说明 embedding / reranker / 数据库链路正常。测试 bank 可在 Web UI 删除（见 §15）。

---

## 10. systemd 服务化

日志不进 journald，由 systemd 直接追加写文件，再由 Alloy 的 `loki.source.file` tail 推进 Loki（见 [[监控告警链路追踪/Alloy/实践/Alloy 采集 Loki 日志实战记录.md]]）。**日志目录要先建**，systemd 不会替你建：

```bash
mkdir -p /var/log/hindsight
```

> 目录不存在时服务会启动失败（通常是 `status=209/STDOUT`）。也可以在 `[Service]` 里加 `LogsDirectory=hindsight` 让 systemd 自己建，就不用手动 `mkdir`。

`/etc/systemd/system/hindsight.service`（线上实际使用的版本）：

```ini
[Unit]
Description=Hindsight memory API
After=network-online.target
Wants=network-online.target

[Service]
EnvironmentFile=/opt/hindsight/hindsight.env
ExecStart=/opt/hindsight/.venv/bin/hindsight-api
Restart=on-failure
RestartSec=5
# 升级/换模型需重新下载时留余量
TimeoutStartSec=600

# 日志落到 /var/log/hindsight/，由 alloy loki.source.file tail
StandardOutput=append:/var/log/hindsight/hindsight.log
StandardError=append:/var/log/hindsight/hindsight.err.log

[Install]
WantedBy=multi-user.target
```

> host/port 已在 env 中设置，`ExecStart` 不再重复传参，避免两处不一致。不需要 `source .venv/bin/activate`。
>
> 相比早先的版本去掉了 `Type=simple`（默认值，等价）和 `WorkingDirectory=/opt/hindsight`。去掉后进程工作目录是 `/`，只有服务写相对路径文件时才需要加回来。

```bash
systemctl daemon-reload
systemctl enable --now hindsight
systemctl is-enabled hindsight && systemctl is-active hindsight
ss -lntp | grep 8888          # 期望: 127.0.0.1:8888
```

> 目前以 root 运行。改为专用用户时：`useradd -r -s /usr/sbin/nologin hindsight && chown -R hindsight: /opt/hindsight`，并在 `[Service]` 加 `User=hindsight`，否则会因无权读取缓存而重新下载模型。

---

## 11. 运维

应用日志在文件里（§10），**`journalctl -u hindsight` 现在只剩 systemd 自己的启动/停止/失败记录，看不到应用输出**：

```bash
tail -f /var/log/hindsight/hindsight.log /var/log/hindsight/hindsight.err.log   # 实时看应用日志
journalctl -u hindsight -n 50 --no-pager   # 只看服务启停/崩溃记录
systemctl restart hindsight
```

Loki 里等价的查询是 `{job="hindsight"}`，可以按 `level`、`stream` 再筛。

### 日志轮转（建议，尚未配置）

`append:` 只追加不轮转，文件会一直长大。systemd 一直持有文件句柄，轮转要用 `copytruncate`，用 rename + create 的话 systemd 会继续写进被改名的旧文件。`/etc/logrotate.d/hindsight`：

```text
/var/log/hindsight/*.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

> `copytruncate` 在复制和清空之间可能丢几行；Alloy 侧遇到文件被截断时的行为我没有验证过，上线后观察一次轮转前后 Loki 里日志是否连续。

### 升级

```bash
systemctl stop hindsight
uv pip install --python /opt/hindsight/.venv/bin/python -U hindsight-api --torch-backend cpu
uv pip check --python /opt/hindsight/.venv/bin/python
systemctl start hindsight && tail -f /var/log/hindsight/hindsight.log /var/log/hindsight/hindsight.err.log
```

> 不带 `--torch-backend cpu` 升级会把 CUDA torch 和 nvidia-* 装回来。

### 资源参考

| 项 | 实测 |
|---|---|
| 进程 RSS | ~3.3 GB |
| venv | ~2.0 GB |
| 模型缓存 | bge-m3 同时下了 `pytorch_model.bin` 与 `model.safetensors`（各 2.27 GB），加 reranker 约 6–7 GB |

---

## 12. 踩坑记录

| # | 现象 | 原因 | 处理 |
|---|---|---|---|
| 1 | `LLM API key is required` | Hermes 用 `HINDSIGHT_LLM_API_KEY`，独立 API 读 `HINDSIGHT_API_LLM_API_KEY`；或 env 没 source（重启/新开 Shell 后） | 用 env 文件 + systemd `EnvironmentFile=` |
| 2 | 日志 `LLM: provider=openai, model=gpt-4o-mini`、`Database: pg0` | env 未加载，全部走默认值 | 同上；启动先核对前两行日志（`/var/log/hindsight/`，见 §10） |
| 3 | MiniMax `401 invalid api key (2049)` | `provider=minimax` 默认 endpoint 是国际站 `api.minimax.io`，国内 Key 需 `api.minimaxi.com` | 显式设置 `HINDSIGHT_API_LLM_BASE_URL` |
| 4 | `vector.control: No such file` | pgvector 装在了客户端而不是 DB Server | DB VM 安装 `postgresql-16-pgvector` |
| 5 | `Model/connection initialization did not complete within 300s` | 首次启动边下载模型边初始化，超时 | 先 `hf download` 预下载（§6），或调大 `HINDSIGHT_API_MODEL_INIT_TIMEOUT` |
| 6 | 加载模型 OOM / 卡死 | VM 仅 2 GB 内存 | 调到 8 GB，PVE 关机再开机 |
| 7 | venv 6.4 GB | `uv pip install` 默认装 CUDA torch | `--torch-backend cpu`（§4） |
| 8 | `uv pip ...` 报 `No virtual environment found` 或装进 `/usr` | 不在 venv 目录且未激活 | 一律加 `--python /opt/hindsight/.venv/bin/python` |
| 9 | 换 embedding 模型后启动报 `Cannot change embedding dimension ... contains N rows` | 表中已有向量数据 | **空表会自动 `ALTER` 到新维度并重建 HNSW 索引**；有数据则需清空重新 embedding，所以模型要在正式写入记忆前定好 |
| 10 | `modules.json` / `2_Normalize/config.json` 404 | sentence-transformers 探测可选文件 | 无害，只要后续出现 `provider initialized` |
| 11 | `unauthenticated requests to the HF Hub` | 未设 `HF_TOKEN` | 无害，只影响下载限速 |
| 12 | `HINDSIGHT_IDLE_TIMEOUT` 不生效 | v0.10.1 无此变量；`--idle-timeout` 参数已废弃并被忽略 | 删除 |
| 13 | tzlocal 警告 `/etc/timezone` 与 `/etc/localtime` 不一致 | 系统遗留配置 | `timedatectl set-timezone Asia/Shanghai` |

---

## 13. 最终检查清单

```bash
systemctl is-enabled hindsight        # enabled
systemctl is-active hindsight         # active
ss -lntp | grep 8888                  # 127.0.0.1:8888
free -h                               # total ≈ 7.7Gi
hermes memory status                  # available
tail -n 300 /var/log/hindsight/hindsight*.log | grep -E "Database:|LLM:|Connection verified|initialized \(|dimension|startup complete"
```

---

## 14. 安全

- `hindsight.env` 权限 `600`；`.env`、数据库 URL、API Key 不进 Git。
- 排查环境变量时脱敏输出（§8）。
- 凭据一旦出现在聊天记录、日志或截图中（**包括打码截图**），视为已暴露并轮换：MiniMax Key、DB 密码。
- Hindsight 仅监听 `127.0.0.1`；默认 REST API 无鉴权，需要跨机访问时经 Caddy 反代并加认证，不要直接 frp 暴露。
- PostgreSQL `pg_hba.conf` 只放行 Agent VM 的 `/32`。

---

## 15. Web UI（Control Plane）

Hindsight 官方 Web UI 走 `npx` 临时运行，不用装 Node 包到系统里：

```bash
npx @vectorize-io/hindsight-control-plane --api-url http://127.0.0.1:8888
```

- `npx` 会把包和依赖下载到本机 npm 缓存（`~/.npm/_npx/`），**不是全局安装**，不会污染系统，但会占磁盘空间。不想要了直接 `rm -rf ~/.npm/_npx` 清掉。
- Node 最低版本要求未核实过，`npx` 启动时如果报版本不对，按提示装对应的 LTS 版本即可（Ubuntu 24.04 apt 源里的版本偏旧，可能需要单独装）。

### 跑在哪台机器上

Hindsight API 只监听 `127.0.0.1:8888`（§14），Web UI 本质是个连这个本地端口的前端，**跑在哪台机器上就只能连那台机器自己的 8888**。按"Agent 相关的东西全放在 Agent VM"的分工，Web UI 也放 Agent VM 上跑，Mac 只负责开浏览器：

```bash
# Agent VM 上
node -v    # 没有 Node 或版本太旧，先装 Node LTS
npx @vectorize-io/hindsight-control-plane --api-url http://127.0.0.1:8888
```

### 从 Mac 访问

UI 起在 Agent VM 上，端口不对外开放（符合 §14 的最小暴露原则），从 Mac 访问靠端口转发，二选一：

- **VS Code Remote SSH**：连上 Agent VM 后，VS Code 通常会自动把 `9999` 转发到 Mac 本地，转发不了就去「端口」面板手动添加
- **SSH 隧道**：Mac 上执行
  ```bash
  ssh -N -L 9999:127.0.0.1:9999 root@<AGENT_VM_IP>
  ```

两种方式选一个跑起来之后，Mac 浏览器打开 `http://localhost:9999` 即可。
