---
publish: true
---

> 基于 Hindsight 官方文档 **1.2.x**（对应本地 `hindsight-api 1.2.1`）整理，2026-11-15 抓取。
> 官方文档站：https://hindsight.vectorize.io/developer/
> **版本对应**：文档站无版本前缀的路径 = 1.2.x（当前）；`/1.0/` `/1.1/` `/0.10/` 是历史快照，**不要看**。
> 部署 SOP 见 [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]]。

---

## 0. 三层记忆模型（最重要的一张表）

Hindsight 的知识分三层，**reflect 的检索阶梯从上往下走**：

| 层 | 谁产生 | 粒度 | 例子 |
|---|---|---|---|
| **Mental Models** | **你手动指定题目** | 一整篇文档 / 一个问题 | 「阿B画像」整篇文档 |
| **Observations** | Consolidation 自动 | 一条信念 / 一个事实簇 | 「阿B偏好可读性强的代码」 |
| **Raw Facts** | Retain 自动 | 一条陈述 | 「阿B用 Java 写 ShiftBalance」 |

**关键点：层与层之间是"越来越便宜的沉淀版本"。** mental model 命中且新鲜时，reflect 直接用它作答，不再往下检索。

| 操作 | 干什么 | 返回 | 你的实测耗时 |
|---|---|---|---|
| **Retain** | 存记忆，LLM 抽取事实+情绪+推理 | 无（纯写入） | ~20s/批（含 embed） |
| **Recall** | 检索原始事实 | 结构化事实列表，原样 | **~34s**（瓶颈=重排） |
| **Reflect** | **跑自主 agent 循环**，多轮工具调用 | **LLM 合成**的 markdown 答案 | **276–298s**（mental model 刷新） |

**Recall vs Reflect**：Recall 是"查表"，Reflect 是"想清楚再回答"。

---

## 1. Mental Models（mental-model 是什么、为什么只有 2 篇）

> 官方页：`/developer/mental-models`（概念）· `/developer/api/mental-models`（API）

### 本质

> A mental model is **a standing answer to a question** about a bank.
> You define the question once; Hindsight writes the answer, keeps it stored,
> and rewrites it in the background as the bank learns more.

**mental model = 保存下来的 reflect 结果**。创建时跑一次 reflect，把结果存下来；之后每次 reflect 会**优先检查 mental model**。

**为什么值得用**（官方原话）：
- **Speed** — 读取 mental model 是**纯数据库读**，无检索、无合成、无 LLM 调用、不等待
- **Consistency** — 两个人问同一个问题得到**同一篇文档**，不是两份独立生成、细节互相矛盾的答案
- **Provenance** — 记录了它由哪些 fact/observation 构成，**保留每个版本的 previous_content**，能查"上个月它怎么说"

### ⚠️ 数量由你决定，不是自动发现的

**mental model 不会自动新增。** 你库里只有 2 个，因为当初只定义了 2 个题目：

| ID | source_query | max_tokens | subtype |
|---|---|---|---|
| `user-profile` | 「阿B是谁？背景、当前工作、职业方向、偏好的沟通方式和协作习惯。」 | 1024 | `pinned` |
| `homelab-architecture` | 「阿B的 homelab 现在的架构：PVE 宿主机、各 VM 的编号/角色/IP、网络与反代、监控、存储」 | 2048 | `pinned` |

创建：
```bash
hindsight mental-model create "$BANK_ID" "名称" "题目" --id my-model
```
返回 `operation_id`，后台跑 reflect，完成后存下。

**自定义 ID 规则**：小写字母数字 + 连字符，最长 192 字节 UTF-8，不能含 `/` 和控制字符。ID 重复则请求被拒。

---

## 2. Mental Model 刷新机制（`retry_blocked` 的官方解释）

### 触发方式（`trigger` 对象）

| 字段 | 默认 | 说明 |
|---|---|---|
| `mode` | `full` | `full` 全文重写 / `delta` 增量改写 |
| `refresh_after_consolidation` | **false** | 每次 consolidation 后刷新 |
| `refresh_cron` | null | UTC 5 段 cron，如 `"0 3 * * *"` = 每天 UTC 03:00 |
| `full_refresh_cron` | null | delta 模式的定期全量重写，如 `"0 3 * * 0"` = 每周日 UTC 03:00 |
| `min_refresh_interval_seconds` | null | 两次自动刷新之间的最小间隔 |
| `budget` | null | agent 步数倍率：`low` 减半 / `mid` 不变 / `high` 加倍（相对 `reflect_max_iterations`） |
| `tags_match` | null | `any` / `all` / `any_strict` / `all_strict` / `exact`；带 tag 的模型默认 `all_strict` |
| `fact_types` | null | 限定读取 `world` / `experience` / `observation`，null = 全部 |
| `exclude_mental_models` | false | 隐藏其他 mental model，防止自我合成 |
| `keep_trace` | false | 记录每次刷新怎么得出的结果 |

> **`refresh_cron` 和 `refresh_after_consolidation` 互斥** —— 一个模型要么按 consolidation 触发，要么按固定 cron，不能都要。

### 你踩的坑：`retry_blocked=2` 的确切机制

> **官方原文**：
> A failed refresh **pauses the automatic ones**. A failed refresh is retried by the worker
> (`HINDSIGHT_API_WORKER_MAX_RETRIES`, 3 by default) **and then stops**.
> **None of `refresh_after_consolidation`, `refresh_cron` or `full_refresh_cron` queues that model again
> until a refresh succeeds** —— so a refresh that cannot work costs a few attempts instead of
> an LLM bill every tick.
>
> A refresh cut off by `HINDSIGHT_API_REFLECT_WALL_TIMEOUT`, **which bounds a whole refresh the same way
> it bounds a reflect, counts as a failure too.**

**翻译成人话**：
1. 刷新失败 → worker 重试 3 次 → 然后**彻底停止**
2. **不是"暂停"，是"直到你手动刷新成功前，自动触发器再也不会排队它"**
3. 被 `REFLECT_WALL_TIMEOUT` 掐断 = 失败（你之前 300s 墙钟不够 reflect 的 276–298s + 余量，所以每次必败）
4. 修好原因后**手动刷一次就恢复自动**

### 解法

```bash
# 手动刷新（忽略 min_refresh_interval 地板，立即执行）
hindsight mental-model refresh "$BANK_ID" "$MENTAL_MODEL_ID"
```
官方明确：*"Explicit refreshes (API, MCP, control plane) **ignore the floor and run immediately**, and additionally release a parked refresh if one is waiting."*

### 监控告警

```
GET /v1/default/banks/{bank_id}/stats  →  paused_mental_models
```
**这个值 > 0 就该告警** —— 表示有模型停止自我更新了。

### 历史记录

```bash
hindsight mental-model history "$BANK_ID" "$MM_ID"
```
失败也会记录，`kind: refresh_failed`，带 `failure_reason`：
`retrieval_failed` / `no_answer` / `unexpected_error` / `empty_candidate` /
`structured_doc_unreadable` / `delta_ops_failed` / `delta_ops_all_skipped` /
`delta_not_applied` / `structured_output_failed` / `candidate_rejected`

版本历史上限默认 50 条/模型（`HINDSIGHT_API_MENTAL_MODEL_HISTORY_MAX_ENTRIES`），
**失败记录与版本记录分开计数**，失败再多也不会挤掉版本历史。

### `min_refresh_interval_seconds` 的真实语义（重要）

> A trigger that fires inside the window is **not dropped**. Its refresh is **queued and parked**
> until the window closes, and every further trigger in the meantime **folds into that same queued
> refresh** —— so a burst of twenty retains costs one refresh, and that refresh still reads
> everything the twenty retains added. The only thing you trade away is **immediacy**.

**不是"丢弃触发"，是"合并成一次"。** 窗口期内攒的所有新记忆，窗口关闭后一次全部读进去。
唯一代价：模型最多滞后一个间隔。

- 层级：per-model 的 `trigger.min_refresh_interval_seconds` > per-bank 的 `mental_model_min_refresh_interval_seconds` > server 级 `HINDSIGHT_API_MENTAL_MODEL_MIN_REFRESH_INTERVAL_SECONDS`
- **默认全是 0（无地板）**
- `min_refresh_interval_seconds: 0` 可以让某个模型豁免 bank 级地板
- 排队期间 operation 保持 `pending`，`next_retry_at` = 窗口关闭时刻，`GET /operations` 能看到它在等什么

### `full` vs `delta` 模式

| 模式 | 行为 | 适用 |
|---|---|---|
| `full`（默认） | 每次从头重新生成整篇 | 文档短、想让每次刷新重构结构、还没定形 |
| `delta` | 只应用**类型化操作**，其余**逐字节复制** | 长期"手册"型文档，要稳定不被改写 |

`delta` 的操作集：`add_section` / `remove_section` / `rename_section` /
`replace_section_blocks` / `append_block` / `insert_block` / `replace_block` / `remove_block`

**为什么需要 delta**（官方解释得很准）：
> "preserve the unchanged content" 对 LLM 只是个**软约束** —— 它本质上就是从输入的整体感觉里生成下一个 token，
> 所以被要求"保持不变"的散文在多次刷新后会**漂移**。delta 模式下未提及的 block **物理上不碰**，
> 表格还是表格。

section 和 block 按 **id** 寻址，不按位置 —— 不会因为数错而改错地方。
失败模式保守：引用不存在的 section/block 的操作**被丢弃而非猜测**，其余操作照常生效。

### Staleness Gating（新鲜度门控）

模型被交给 reflect agent 时会带一个**新鲜度信号** —— "since it was last written，它作用域内有没有新记忆落地"。
落后的模型**仍然会被展示**，但**不再短路检索**，agent 应当拿它跟下层核对而不是盲信。

---

## 3. Observations（为什么改不了 observation）

> 官方页：`/developer/observations`

**Observation = consolidation 自动产出的"有证据支撑的信念"**。

| 原始 fact | Observation |
|---|---|
| "Alice prefers Python" | "Alice 是重视可读性与简洁的 Python 开发者" |
| "Alice dislikes verbose code" | |
| "Alice recommends type hints" | |

**四个特性**：
1. **Deduplication** —— 一条持久的信念，替代多条重叠 fact
2. **Grounding** —— 每条 observation 引用具体源记忆（**带原文引用**）
3. **Evolution** —— 证据增强/削弱/矛盾时**被精炼而非覆盖**，历史保留
4. **Freshness awareness** —— 新记忆还没 consolidation 时，`reflect` 把受影响的 observation 当作 **stale**，并**去和 raw fact 核对**

### consolidation 流程

`retain()` 完成后自动后台跑：
1. **新 fact 分析** —— 每条新 fact 与已有 observation 比对
2. **模式检测** —— 相关 fact 分组并综合
3. **observation 创建/更新** —— 新建或精炼已有
4. **证据追踪** —— 维护支撑 fact 的引用

**这就是为什么你改一条 world 记忆，会连带触发派生 observation 重建、re-consolidation 和图维护。**

**Decision-Model Triage**（1.x 新增，未启用）：配了 decision model 时，它先替 consolidation LLM 处理简单 fact ——
复述已有 observation → 作为证据挂上；闲聊 → 跳过；改变/新增 → 才交给 LLM。
**decision model 永远不写 observation 的文本。**

---

## 4. Retain（记忆是怎么被抽出来的）

> 官方页：`/developer/retain`

**不止存"说了什么"，还存"为什么、怎么、意味着什么"。**

例：`retain("Alice joined Google last spring and was thrilled about the research opportunities")` 抽出：
- 核心事实：Alice 加入 Google / 发生在去年春天
- 情绪与意义：她很兴奋 / 这代表重要机会
- 推理：她为了研究机会选择加入

→ 之后问 "Why did Alice join Google?" 得到有意义的答案，而不是干巴巴一句"她加入了 Google"。

### 两类 fact（由「谁在说」决定，不是语法）

| 类型 | 抓什么 | 例 |
|---|---|---|
| `experience` | **bank 自己的 agent** 的第一人称历史 | 「我 patch 了那个鉴权 bug」 |
| `world` | 关于其他人/事/物的 | 「Alice 在 Google 工作」 |

> A first-person statement is an `experience` **only when the speaker is the bank's agent**.
> 同样的词，别人说出来就是关于那个人的 `world` fact。

**怎么控**：在每条 item 的 `context` 里描述说话人。
- 转录第三方内容 → `"Customer Maria is speaking"`
- agent 自己的日志 → `"The assistant is speaking"`

---

## 5. Recall（检索链路 & 重排参数）

> 官方页：`/developer/api/recall`

官方标称延迟（**注意这是理想值，你的环境差一个数量级**）：

| 操作 | 标称延迟 | 主要瓶颈 | 优化手段 |
|---|---|---|---|
| Recall | 100–600ms | Re-ranker（CPU 上） | 用 GPU 重排，或减小 budget |
| Reflect | 800–3000ms | LLM 生成 | 换更快的 LLM |
| Retain | 500–2000ms/批 | LLM fact 抽取 | 高吞吐 LLM provider |

**官方设计哲学：优先优化读，不优化写。** 事实抽取在写入时做完，检索时只做 ANN + 重排。

### 重排相关变量（你环境的关键项）

| 变量 | 默认 | 说明 |
|---|---|---|
| `HINDSIGHT_API_RERANKER_LOCAL_MODEL` | `hindsight-ai/hs-rerank-1` | **你用的是 `BAAI/bge-reranker-base`** |
| `HINDSIGHT_API_RERANKER_LOCAL_MAX_CONCURRENT` | `4` | 并发重排数，防 CPU 抖动。**你实测过改 1 无收益，已回滚** |
| `HINDSIGHT_API_RERANKER_LOCAL_BATCH_SIZE` | `32` | 批大小，"smaller batches can outperform larger ones" |
| `HINDSIGHT_API_RERANKER_LOCAL_BUCKET_BATCHING` | `false` | **按 token 长度排序后再批，减少 padding 浪费，官方称快 36–54%，质量不变** |
| `HINDSIGHT_API_RERANKER_LOCAL_TIMEOUT` | `300` | 单次 recall 候选打分的墙钟上限；**超时后未打分的候选保留 RRF 顺序，recall 照常返回** |
| `HINDSIGHT_API_RERANKER_LOCAL_FP16` | `false` | CUDA 上更快；CPU 缺原生 FP16 支持，故默认关 |
| `HINDSIGHT_API_RERANKER_LOCAL_FORCE_CPU` | `false` | 有 CUDA 时仍强制 CPU |

> ⚠️ **`RERANKER_MAX_CANDIDATES` 在 1.x 文档里是"链级"设置** —— 你可以从 `RERANKER_LOCAL_MAX_CANDIDATES`（或 `RERANKER_MAX_CANDIDATES`）改成**多 provider 链**：
> `RERANKER_1_PROVIDER=cohere` → `RERANKER_2_PROVIDER=rrf`。
> **以 `rrf` 结尾 = fail open**：reranker 全挂时按检索阶段原始顺序返回，不报错。

---

## 6. Reflect（为什么 276–298 秒）

> 官方页：`/developer/reflect`

**agent 循环可用的工具**：

| 工具 | 用途 | 优先级 |
|---|---|---|
| `search_mental_models` | 用户策展的总结 | **最高（先查）** |
| `read_mental_models` | 拿到 snippet 后的全文 | snippet 看着相关时 |
| `search_observations` | 综合后的知识 | 高 |
| `recall` | 原始事实（ground truth） | 兜底 |
| `expand` | 取某条记忆的更多上下文 | 需要时 |
| `done` | 给出最终答案 | 准备好时 |

**约束**：
- **必须先收集证据再回答**（guardrail 防止空响应）
- 最多跑 **10 轮**（`HINDSIGHT_API_REFLECT_MAX_ITERATIONS`）
- **校验引用** —— 只有真正检索到的 ID 才能被引用

### Reflect 相关变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `HINDSIGHT_API_REFLECT_MAX_ITERATIONS` | `10` | 强制出答案前的最大工具调用轮数 |
| `HINDSIGHT_API_REFLECT_WALL_TIMEOUT` | `300` | 整个 reflect 的墙钟上限；超时返回 HTTP 504。**同时也约束 worker 里的 mental model 刷新 —— 超时的刷新被取消并标记失败，而不是占着 worker slot** |
| `HINDSIGHT_API_REFLECT_MAX_CONTEXT_TOKENS` | `100000` | 强制最终合成前的 context token 上限，防 `context_length_exceeded` |
| `HINDSIGHT_API_REFLECT_MISSION` | - | 全局 reflect 任务书（身份与推理框架），可被 per-bank config 覆盖 |
| `HINDSIGHT_API_REFLECT_DEFAULT_OPTIONS` | - | **mental model 刷新不读这个**（见下方注意点） |
| `HINDSIGHT_API_LLM_TEMPERATURE_REFLECT` | - | reflect 专用温度 |
| `HINDSIGHT_API_LLM_TEMPERATURE_MENTAL_MODEL_REFRESH` | - | 刷新 delta/retract 专用温度（1.x 新增，可与 reflect 分开调） |
| `HINDSIGHT_API_MENTAL_MODEL_REFRESH_LLM_API_KEY` | - | 刷新可用独立 LLM/凭据 |

> **官方明确**：刷新**不读** bank 的 `reflect_default_options`，
> 而 `reflect_search_observations_max_tokens` 默认用**内置的 5000**。
> 想改要用 `trigger.reflect_search_observations_max_tokens` 覆盖。
> 同理 `trigger.reflect_search_observations_include_entities`（默认开启，实体名可能占一半 payload）。

### Decision-Model Orchestration（1.x 新增，未启用）

配了 decision model 时，循环形状变了，**省 LLM 调用**：
1. 一次 LLM 调用把请求重写成检索 query
2. 所有检索层（mental model / observation / raw fact）**并行**跑这个 query
3. decision model 剪枝证据，并判断是否已经能回答
4. 能 → 下一次 LLM 调用直接出答案；不能 → LLM 写新 query，再来一轮并行

**decision model 失败时退回 agent turns。**

---

## 7. 配置速查（595 个环境变量里的关键项）

> 官方页：`/developer/configuration`
> 全量变量表在官方站，本文只列与本环境相关的。

### 当前环境实际生效的配置

`/opt/hindsight/hindsight.env`（权限 600）：

```ini
HINDSIGHT_API_DATABASE_URL=postgresql://...@192.168.31.5:5432/hindsight
HINDSIGHT_API_LLM_PROVIDER=minimax
HINDSIGHT_API_LLM_MODEL=MiniMax-M2.7-highspeed
HINDSIGHT_API_LLM_BASE_URL=https://api.minimaxi.com/v1   # 国内站，国际站是 api.minimax.io
HINDSIGHT_API_LLM_API_KEY=***
HINDSIGHT_API_EMBEDDINGS_PROVIDER=local
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3          # dim=1024
HINDSIGHT_API_RERANKER_PROVIDER=local
HINDSIGHT_API_RERANKER_LOCAL_MODEL=BAAI/bge-reranker-base
HINDSIGHT_API_RERANKER_MAX_CANDIDATES=50                 # 11-01 事故后从 300 降下来
HINDSIGHT_API_REFLECT_WALL_TIMEOUT=900                    # 从 300 抬上来
HINDSIGHT_API_HOST=127.0.0.1
HINDSIGHT_API_PORT=8888
HF_HOME=/opt/hindsight/hf-cache
```

bank 级配置（存 `banks.config` JSON，可用 bank config API 改）：

```json
{
  "mental_model_min_refresh_interval_seconds": 86400,
  "retain_mission": "只保留关于阿B长期有效的信息：...",
  "observations_mission": "把零散事实整合成稳定结论：...",
  "enable_observations": true,
  "recall_include_chunks": true,
  "retain_extraction_mode": "concise",
  "store_document_text": true,
  "memory_defense": {"enabled": true, "rules": [{"on": "sensitive_data", "action": "redact"}]}
}
```

### 值得注意的默认值陷阱（官方配置页明确列出）

| 变量 | 不设的后果 |
|---|---|
| `HINDSIGHT_API_HOST` | `0.0.0.0` → **全 LAN 暴露** |
| `HINDSIGHT_API_EMBEDDINGS_PROVIDER` | `bge-small-en-v1.5` → 纯英文，中文召回差 |
| `HINDSIGHT_API_LLM_PROVIDER` | `openai/gpt-4o-mini` |
| `HINDSIGHT_API_DATABASE_URL` | 内嵌 `pg0` |
| `HINDSIGHT_API_MODEL_INIT_TIMEOUT` | `300` 秒；首次启动边下载模型边初始化会超时 |

### Worker 相关

| 变量 | 默认 | 说明 |
|---|---|---|
| `HINDSIGHT_API_WORKER_MAX_RETRIES` | `3` | **mental model 刷新失败重试 3 次后停止**（你的 `retry_blocked` 就是这个） |
| `HINDSIGHT_API_WORKER_TASK_RETRY_BACKOFF_SECONDS` | `60` | 失败重试间隔 |
| `HINDSIGHT_API_WORKER_ID` | hostname | **生产建议设成稳定值** —— 容器重建后 ID 变了，in-flight 任务会永久搁浅没人认领 |
| `HINDSIGHT_API_WORKER_POLL_INTERVAL_MS` | `500` | 轮询间隔 |
| `HINDSIGHT_API_WORKER_MAX_SLOTS` | - | 最大并发 slot |
| `HINDSIGHT_API_WORKER_CONSOLIDATION_RESERVED_SLOTS` | - | consolidation 预留 slot |

### Mental Model 相关

| 变量 | 默认 | 说明 |
|---|---|---|
| `HINDSIGHT_API_MENTAL_MODEL_MIN_REFRESH_INTERVAL_SECONDS` | `0` | server 级地板 |
| `HINDSIGHT_API_ENABLE_MENTAL_MODEL_HISTORY` | `true` | 关掉则不写历史行（省存储） |
| `HINDSIGHT_API_MENTAL_MODEL_HISTORY_MAX_ENTRIES` | `50` | 每模型保留版本数 |
| `HINDSIGHT_API_MENTAL_MODEL_DELTA_USE_DECISION_MODEL` | - | delta 刷新用 decision model |
| `HINDSIGHT_API_MENTAL_MODEL_DELTA_GATE_MAX_MEMORIES` | - | delta 门控的记忆数上限 |

---

## 8. 运维接口

> 官方页：`/developer/admin-cli` · `/developer/monitoring`

```bash
hindsight mental-model list   "$BANK_ID"
hindsight mental-model get    "$BANK_ID" "$MM_ID"
hindsight mental-model create "$BANK_ID" "名称" "题目" --id my-model
hindsight mental-model refresh "$BANK_ID" "$MM_ID"     # 手动刷新，忽略地板
hindsight mental-model history "$BANK_ID" "$MM_ID"
hindsight mental-model clear   "$BANK_ID" "$MM_ID"
hindsight mental-model delete  "$BANK_ID" "$MM_ID"
```

**监控**：`/metrics`（Prometheus 格式），重点看：
- `paused_mental_models`（bank stats 里也有）—— **>0 就是有模型停止自我更新，应告警**
- worker slot 使用率、`async_operations` pending 数

---

## 9. 待验证项（本环境尚未确认）

| # | 待验证 | 为什么重要 | 怎么测 |
|---|---|---|---|
| 1 | `RERANKER_LOCAL_BUCKET_BATCHING=true` | 官方称快 36–54%，质量不变 | 同一 query 串行对照 |
| 2 | 切到官方默认 reranker `hindsight-ai/hs-rerank-1` | 官方首推模型，可能比 bge-reranker-base 更准 | 装完做召回准确率对照 |
| 3 | `min_refresh_interval_seconds` 能否救回 `retry_blocked` | 官方说 parked refresh 会合并；但 **failed ≠ parked**，需确认 | 手动 refresh 一次后看是否恢复自动 |
| 4 | `mode: delta` 是否适合 `homelab-architecture` | 该文档长期演进，delta 能防漂移 | 改 trigger 后观察若干次刷新 |
| 5 | `refresh_cron` 替代 `refresh_after_consolidation` | 两者互斥；cron 更可预测 | 改成 `"0 3 * * *"`（UTC 03:00 = CST 11:00） |

---

## 相关文档

- [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]] — 部署与运维 SOP
- [[homelab/AI Agent/Hindsight/Hindsight Memories API.md]]
- [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]]
- [[homelab/AI Agent/Hindsight/Hindsight Reflect API.md]]
- [[homelab/AI Agent/Hindsight/Hindsight Bank Templates.md]]
- [[homelab/05-事件记录/2026-11-01-hindsight-rerank-timeout.md]] — 重排超时事故
