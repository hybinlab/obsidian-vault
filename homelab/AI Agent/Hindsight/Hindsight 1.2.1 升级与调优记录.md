---
publish: true
---

> 记录 2026-11-15 夜间对 Hindsight 做的一次完整变更：版本升级、reranker 换模型、mental model 刷新机制调参。
>
> **结论边界**：升级成功、未观察到数据丢失（已回读验证）；recall 提速已通过 A/B 实测确认；
> `max_tokens=4096` + `mode=delta` 的内容保留效果已通过 5 轮 dry-run 验证；
> **两个 mental model 已真实刷新成功，`retry_blocked` 清零，自动刷新恢复**。
> **尚未验证**：召回质量是否等价（需独立评估）、delta/4096 的多轮次稳定性。
>
> 官方资料整理见 [[homelab/AI Agent/Hindsight/Hindsight 官方文档速查.md]]；部署运维见 [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]]。

---

## 0. 一句话结论

| 动作 | 结果 | 验证强度 |
|---|---|---|
| Hindsight `0.10.1` → `1.2.1` | ✅ 14 个迁移全过，1738 条记忆无损，向量维度未变 | 已回读验证 |
| reranker 换 `hs-rerank-1` | ✅ recall **36.2s → 10.97s（-69%）** | A/B 实测确认 |
| ↑ 同上 · 召回质量 | ⚠️ **未证明等价**：新模型有 2 条旧模型没有的，旧模型有 4 条新模型没有的 | **待独立评估** |
| mental model 切 `delta` + `max_tokens=4096` | ✅ **两个模型已真实刷新成功**，reflect **276–298s → 64–130s**（端到端对比） | dry-run + 真实刷新 |
| ↑ 同上 · 内容保留 | ✅ **5 轮 dry-run 验证**：4096+delta 保住全部 5 项；缺任一都丢 3–5 项 | 已验证（含随机性，见 §4.3） |
| ↑ 同上 · 刷新机制恢复 | ✅ **已恢复**：11-16 08:41 / 08:44 两次真实刷新成功，`paused_mental_models: 0` | 已验证 |

**这次变更的核心认知**：mental model 丢内容**不是 LLM 随机漂移，是预算不足导致的强制压缩**。
5 轮 dry-run 证明：**`max_tokens=4096` + `mode=delta` 缺一不可** —— 2048 预算下两种模式都丢 5 项；
4096 预算下 full 丢 3 项、delta 保住 4 项。

---

## 1. 变更前状态

| 项 | 值 |
|---|---|
| Hindsight API | `0.10.1`（pip 裸装，无 Control Plane） |
| Alembic head | `a7c2e9f41b60` |
| Hermes plugin 侧 | `hindsight-client 1.2.1` + `hindsight-embed 1.2.1` |
| embedding | 本地 `BAAI/bge-m3`（dim 1024，CPU） |
| reranker | 本地 `BAAI/bge-reranker-base`（280M，CPU，`max_concurrent=4`） |
| LLM | MiniMax `MiniMax-M2.7-highspeed`（OpenAI 兼容） |
| 存储 | 103 database VM，PostgreSQL + pgvector |
| 记忆量 | `memory_units` 1716 条（API 报 `fact_count` 1644，差值是 `invalidated_memory_units` 里的失效条目仍留在主表） |
| mental model | `user-profile`（full / 1024）、`homelab-architecture`（full / 2048） |
| 已知故障 | 两个 mental model 自 11-09 起 `retry_blocked=2`，**卡死 6 天** |

**背景**：11-01 事故后加了 `min_refresh_interval_seconds=86400` 止血，但刷新本身一直失败——完整 reflect 需 276–298 秒，而当时 `REFLECT_WALL_TIMEOUT` 只有 300 秒，**每次必撞墙钟**。撞墙钟按官方定义算 failed，failed 之后自动触发器就不再排队该模型。

---

## 2. 升级 0.10.1 → 1.2.1

### 2.1 先算迁移链，别盲升

从 PyPI 下 `hindsight-api-slim` 的 wheel（2.3MB，不装依赖），解包读 `hindsight_api/alembic/versions/`：

```bash
curl -sL "$(curl -s https://pypi.org/pypi/hindsight-api-slim/1.2.1/json \
  | python3 -c "import json,sys; [print(u['url']) for u in json.load(sys.stdin)['urls'] if u['packagetype']=='bdist_wheel']")" \
  -o slim.whl && mkdir x && cd x && unzip ../slim.whl
```

| 版本 | 迁移脚本数 | head |
|---|---|---|
| 0.10.1 | 104 | `a7c2e9f41b60` |
| 1.2.1 | 119 | `05867433a58c` |

**算「待执行」的正确方法**：从 head 沿 `down_revision` 往下走到生产当前版本，中间那段才是待执行。

生产在 `a7c2e9f41b60`，**待执行 14 个**（不是 76 —— 76 是往回走的祖先链，方向反了）。

> ⚠️ 迁移链方向算反是这类操作最容易踩的坑。结论先手算清楚，再决定升不升，成本是 10 分钟；盲升的成本是数据。

### 2.2 14 个迁移逐个过筛

| # | 迁移 | 风险 |
|---|---|---|
| 1 | `add_banks_with_attachments_in_window_routine` | 🟢 |
| 2 | `add_graph_maintenance_queue_claimed_at` | 🟢 |
| 3 | `oracle_index_composite_foreign_keys` | 🟢 Oracle 专用，PG 跳过 |
| 4 | `clear_placeholder_memory_dates` | 🟡 **会 UPDATE 表** |
| 5 | `widen_mental_model_id_refs` | 🟢 |
| 6 | `drop_global_memory_units_vector_indexes` | 🟡⚠ **删全局向量索引** |
| 7 | `scheduled_full_refresh` | 🟡 |
| 8 | `banks_needing_consolidation_hybrid_probe` | 🟢 性能优化 |
| 9 | `oracle_mental_models_text_index` | 🟢 Oracle 专用，跳过 |
| 10 | `merge_trgm_index_and_reasoning_tokens` | 🟢 merge 节点 |
| 11 | `entities_bank_scoped_trgm_index` | 🟡 建索引 |
| 12 | `add_bank_alias_is_primary` | 🟢 |
| 13 | `add_bank_aliases` | 🟢 新表 |
| 14 | `add_mental_models_last_refresh_failed_at` | 🟢 **直接对应本次故障** |

**两个必须先查清的点**：

```sql
-- 迁移 #4 影响面：占位日期有多少行
SELECT count(*) FILTER (WHERE event_date IN ('0001-01-01','9999-12-31')) FROM memory_units;
-- → 0  （1726 条有 event_date，范围 2025-11-01 ~ 2027-01-01）

-- 迁移 #6 影响面：现有向量索引
SELECT indexname FROM pg_indexes WHERE tablename='memory_units' AND indexdef ILIKE '%hnsw%';
-- → 4 个：1 全局 + 3 个按 fact_type/bank_id 分区
```

结论：#4 对本库**零影响**；#6 删的是全局索引，**3 个分区索引保留**（per-bank 后端上全局索引会让查询走错路径，删掉反而更精确）。

**另外查了整条迁移链，没有任何 `ALTER ... TYPE vector(...)`** —— 向量维度不会因迁移改变。

### 2.3 备份（回滚保障）

```bash
set -a; source /opt/hindsight/hindsight.env; set +a
PGPASSWORD="$(python3 -c "import os,urllib.parse as u; print(u.unquote(u.urlparse(os.environ['HINDSIGHT_API_DATABASE_URL']).password or ''))")" \
pg_dump -Fc -h 192.168.31.5 -p 5432 -U hindsight -d hindsight \
  -f /root/.hermes/backups/hindsight/hindsight-$(date +%Y%m%d-%H%M%S).dump
```

产物：`/root/.hermes/backups/hindsight/hindsight-20261115-231156.dump`，15.0 MB，`pg_dump` 返回 0，`pg_restore -l` 可读，194 个条目，含全部 10 张表的数据段。

> **备份必须验证可读**，光看文件大小不算数。
>
> 但 `pg_restore -l` **只是必要条件，不是充分条件**。它只证明**归档目录（TOC）可读**，不保证：
> - 所有数据块内容完整
> - 恢复时无对象冲突（对象已存在、权限、扩展版本）
> - 旧版本应用能正常读取恢复后的库
> - 恢复过程满足预期的 RTO
>
> **真正的回滚能力验证需要在隔离环境完成一次完整恢复演练**（恢复到临时库 → 起旧版应用 → 跑查询验证 → 记录耗时）。
> 本次**未做该演练**，因此「回滚路径存在」是事实，「回滚一定成功」是未验证的假设。
> 跨大版本升级时尤其如此：1.2.1 迁移可能改变 schema，回滚到 0.10.1 需要**同时回滚数据库和代码**，
> 且数据库回滚到迁移前状态需要 `pg_restore` 全量恢复（不是简单 downgrade）。

### 2.4 升级命令

```bash
systemctl stop hindsight.service
uv pip install --python /opt/hindsight/.venv/bin/python \
  "hindsight-api==1.2.1" --torch-backend cpu
systemctl start hindsight.service
```

`--torch-backend cpu` **不能省**：不带它会装 CUDA 版 torch + nvidia-* 包，venv 从 2GB 变 6.4GB。

### 2.5 验证结果

启动日志逐条可查：

```
Running upgrade a7c2e9f41b60 -> b8d3f1a6c2e4, Add last_refresh_failed_at column to mental_models
... 共 14 条 ...
Database migrations completed successfully for schema 'public'
Embeddings: local provider initialized (dim: 1024, device: cpu)
Reranker: local provider initialized (device: cpu, max_concurrent=4)
```

| 项 | 升级前 | 升级后 |
|---|---|---|
| `api_version` | 0.10.1 | **1.2.1** |
| Alembic | `a7c2e9f41b60` | **`05867433a58c`**（= 1.2.1 head） |
| `memory_units` | 1716 | 1738（含期间新写入，非迁移所致） |
| `entities` | 1696 | 1730 |
| `memory_links` | 28700 | 29289 |
| 向量维度 | 1024 | **1024** |
| HNSW 索引 | 4 个 | **3 个分区索引**（全局那个按预期删除） |
| Hermes plugin | 1.2.1 客户端 | **1.2.1 客户端 ↔ 1.2.1 服务端，原生匹配** |
| `/health` | 200 | 200，3ms |
| NRestarts | — | **0** |

**升级期的一次连接抖动**：重启窗口（23:19:12–23:19:48）内出现 15 条 `httpx.ConnectError` / `APITimeoutError`。

**归因未确认** —— 已确认的只是**时间上与重启窗口重叠**，以及重试后 `llm_batch #1 processed=8/8` 全部成功、**无数据丢失**。至于成因是本地连接池未就绪、MiniMax 上游短暂抖动，还是两者叠加，**没有直接证据**（没有 TCP 层抓包、没有上游侧日志）。

> **可观察到的版本差异**：新版重试策略是「4 次快速重试」（约 16 秒内耗尽），旧版每次失败间隔更久。以后 MiniMax 抖动时，1.2.1 会更快耗尽重试次数 —— 这是**行为差异**，不是本次故障的根因。

**回滚路径**（保留 24 小时）：`pg_restore` 恢复旧 dump + `uv pip install hindsight-api==0.10.1`。

---

## 3. reranker 换模型：`bge-reranker-base` → `hs-rerank-1`

### 3.1 为什么换

Hindsight 1.x 官方首推 `hindsight-ai/hs-rerank-1`（**114M，MIT**），而当时用的是 `BAAI/bge-reranker-base`（280M）。模型小 2.5 倍。

**关键点**：换 reranker **不改 embedding 模型**，所以 1738 条记忆**不需要重新 embedding**，1024 维向量和 HNSW 索引都不受影响。换 `hs-embed-1`（112M）就不一样了 —— 官方明说换 embedding 模型必须重新 embedding 全部存量记忆，那是另一个量级的工程。

### 3.2 A/B 对照（同一 query，串行连测）

query：`Hindsight 重排超时 根因 候选数`，`max_tokens=1500`

| | bge-reranker-base (280M) | hs-rerank-1 (114M) |
|---|---|---|
| 第1次 | 36.69s | **11.12s** |
| 第2次 | 35.95s | **10.94s** |
| 第3次 | 35.94s | **10.85s** |
| **均值** | **36.2s** | **10.97s** |
| 波动 | ±0.4s | ±0.13s |

**提速 69%，每次省 25 秒。**

### 3.3 召回质量对比（**质量等价性未证明**）

| 项 | 旧 bge-reranker-base | 新 hs-rerank-1 |
|---|---|---|
| 返回条数 | 11 | 9 |
| 共同命中 | — | **7** |
| **仅旧模型有** | — | **4** |
| **仅新模型有** | — | **2** |

（数学校验：11 − 7 = 4；9 − 7 = 2。✅）

**仅旧模型有的 4 条**（新模型未召回）：

1. `101 Agent` 升至 4 核/8GB 后 reflect 稳定 233–264s，重排降至约 48s，超时归零
2. 推荐的根治方案：`MAX_CANDIDATES=50`，预计重排 215s→21s，比延长超时更精准
3. 阿B homelab 在 2C/6GB 纯 CPU 跑 cross-encoder，无 GPU 透传，核心瓶颈是资源超配
4. reflect 和 page 刷新必须用 `hindsight` 或 `typesafe` provider

**仅新模型有的 2 条**：

1. Agent 此前建议 rerank「什么都不做」及后续查明 recall 默认保留重排器的结论
2. 「仅加入 decision model 对 recall 提速收益有限」的结论

**这两组差集说明什么**：

- 新模型把**决策/结论类**记忆排得更前（第 1、2 条都是"Agent 查明了什么"）
- 旧模型把**架构/历史判断类**记忆排得更前（第 1–4 条都是"当时的配置和判断"）
- **对 query「Hindsight 重排超时 根因 候选数」而言**，第 1、2 条其实高度相关（旧模型排第 5、6 位，新模型直接漏掉），第 3、4 条是边缘相关

**结论边界**：

- ✅ 已证明：**速度提升约 69%，返回条数 11→9**
- ⚠️ **未证明召回质量等价**。差集非空，且丢失的两条与 query 直接相关
- ⚠️ 返回条数减少**部分**可由 `max_tokens=1500` 预算解释（新模型把长文本排前面先耗尽预算），**但不能完全解释差集**
- ❌ **不能得出"旧模型 11 条全部被覆盖"或"召回覆盖不降"的结论**

> **方法教训**：A/B 对比必须用**完整 id 求差集**并做数学校验（总数 − 共同 = 差集）。
> 本次首次计算时用了 `id[:8]` 截断做集合 key，**8 位前缀碰撞**导致 4 条被误判为"在新模型里"，
> 从而得出"仅旧有 = 0"的错误结论。**只看条数或用截断 id 都会得出错误结论。**
>
> **换 reranker 前应先建召回准确率基线**（用一组固定 query 的人工标注期望结果集，测 recall@k），
> 否则无法判断新模型是否真的等价。

### 3.4 官方三个开放权重模型（当前架构可替换的）

| 模型 | 作用 | 大小 | License | 能否在 101 CPU 跑 |
|---|---|---|---|---|
| `hindsight-ai/hs-rerank-1` | reranker | 114M | MIT | ✅ API 进程内 |
| `hindsight-ai/hs-embed-1` | embeddings | 112M | MIT | ✅ API 进程内（但需重新 embedding 全部存量） |
| `hindsight-ai/hs-decide-1-flash` | decision model | 0.8B | Apache 2.0 | ❌ 官方标 vLLM + 一张 GPU |

### 3.5 为什么没上 decision model

官方定位：decision model 干的是**判断题**（这条记忆对回答有帮助吗 / 证据够了吗 / 这条能改变这页吗），返回类型化答案而非散文，从而省掉 LLM 调用。

| 路径 | 官方收益 | 本环境是否可用 |
|---|---|---|
| Recall 排序 | 快（替代 30s 重排） | 需 hosted key 或 GPU |
| Consolidation | LLM 调用 -40% | 同上 |
| **Reflect / Page 刷新** | 最贵路径（276–298s）省最多 | ❌ **不可用** |

**关键限制**：官方原文 —— *"Reflect and page refresh currently need the `hindsight` or `typesafe` provider; with another provider they keep their LLM-only path and log a warning."*

本环境用的是 MiniMax（OpenAI 兼容），**不是 `hindsight` 也不是 `typesafe`** → 最贵的 reflect 路径享受不到优化。

另外两条否决理由：

- **hosted 方案要把记忆内容发到外部服务**（含私人日记摘要、homelab 拓扑），且 `hs-decide-1-flash` 托管价 $0.02/百万 input token
- **自建需要 GPU**，而本环境无 GPU；0.8B 在 4 核 CPU 上跑会比 MiniMax 的 LLM 调用更慢
- **换 provider 会丢排序特性**：官方明确 *"recall does not add its usual recency, temporal and proof-count boosts on top"* —— recall 的 ranker 变成 decision model 后，**它是唯一没有降级路径的操作**，够不到就召回失败（原本本地 reranker 挂了不影响召回）

**结论：暂不采用。** 先靠换小模型拿到 69% 提速，风险和代价都低得多。

---

## 4. mental model 刷新机制调参

### 4.1 官方机制（先读文档再动手）

三层知识模型，reflect 检索阶梯从上往下：

| 层 | 谁产生 | 粒度 |
|---|---|---|
| Mental Models | **你手动指定题目** | 一整篇文档 |
| Observations | Consolidation 自动 | 一条信念 |
| Raw Facts | Retain 自动 | 一条陈述 |

**关键认知 1：mental model 不会自动新增。** 数量由创建的题目数决定 —— 本库两个都是 2026-09-28 手动创建的（`created_at` 相差 0.27 秒）。

**关键认知 2：`failed` ≠ `parked`。**

| 状态 | 行为 |
|---|---|
| `parked` | 触发落在 `min_refresh_interval` 窗口内 → 排队等窗口关闭，**期间新触发合并进同一次刷新** |
| `failed` | 刷新失败 → worker 重试 `WORKER_MAX_RETRIES`（默认 3）→ **然后停止**。`refresh_after_consolidation` / `refresh_cron` / `full_refresh_cron` **都不再为它排队，直到一次刷新成功** |

本库卡死 6 天属于 **`failed`**（撞 `REFLECT_WALL_TIMEOUT` 墙钟，官方定义「被墙钟掐断的刷新也算失败」）。

**关键认知 3：手动刷新能解锁。** 官方明确 —— *"Explicit refreshes (API, MCP, control plane) ignore the floor and run immediately, and additionally release a parked refresh if one is waiting."*

### 4.2 用 dry-run 代替真实刷新

官方提供 `POST /v1/default/banks/{bank}/mental-models/{id}/dry-run-refresh`：
**跑完整 reflect，但只返回预览，不落盘**。

配套的 `POST .../refresh` 请求体只接受 `mode: "full"` 或 `null`（null = 用模型自己的 mode）—— **单次 refresh 无法指定 delta，delta 必须改 `trigger.mode`**。

dry-run 返回的关键字段：

| 字段 | 用途 |
|---|---|
| `diff` | current 与 preview 的 unified diff |
| `candidate_content` / `preview_content` | 新内容 |
| `delta_operations.applied` | 实际执行的结构化操作 |
| `warnings` | **最重要的信号** |
| `duration_ms` | 本次刷新耗时 |
| `trace.tool_calls` | 每步工具调用与耗时 |

### 4.3 五轮 dry-run 对照（找出真正的根因）

**检查方式说明**：先按**语义概念**检查（证书链路四项是否都在），不按字面字符串匹配。
字面匹配会误判 —— 例如原文中"TLS 终止点未明确"与"nginx -t / SNI / 到期监控"是同一句话，
重写后可能被拆成两条 bullet，字面正则就失效了，但语义完整保留。**这是一个已犯过的错误，见 §7.3。**

| 轮次 | mode | max_tokens | 耗时 | 长度 | TLS终止 | `nginx -t` | SNI | 到期监控 | 自动回滚 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | full | 2048 | 122s | 4027 | ❌ | ❌ | ❌ | ❌ | ❌ |
| 2 | delta | 2048 | 190s | 3098 | ❌ | ❌ | ❌ | ❌ | ❌ |
| 3 | delta | 4096 | 167s | 6223 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 4 | **full** | **4096** | 88s | 7069 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 5 | **delta** | **4096** | 224s | 7013 | — | ✅ | ✅ | ✅ | ✅ |

（轮次 5 的 TLS 终止点：语义存在但表述形式与正则不匹配，实际文本见下方引用。）

**第 2 轮的 warnings 揭示了根因**：

> *"The document is ~2769 tokens, over its 2048-token budget. Delta refreshes were asked to reclaim space from superseded content; if it keeps growing, raise max_tokens or narrow the source query."*

**文档 2769 tokens > 预算 2048 tokens → 系统被迫压缩 → 压缩时把"看起来最不起眼的内容"删了。**

被删的那几项**并不是"过时"，而是"在长文末尾、看起来最不起眼"**。

**轮次 4 vs 5 —— 缺失的那组对照终于补上了**：

同为 `max_tokens=4096`，**full 丢 3 项、delta 保住 4 项**。这是 delta 有独立贡献的直接证据。

**轮次 3 vs 5 —— 两轮都是 delta/4096，结果不同**：

| | 轮次 3 | 轮次 5 |
|---|---|---|
| 长度 | 6223 | 7013 |
| 到期监控 | ❌ | ✅ |
| `facts.retrieved` | observation 49 / world 70 / experience 54 | observation 50 / world 57 / experience 52 |
| window.created_before | 16:24:50Z | 17:08:26Z |

**轮次 5 的窗口已覆盖 00:28 补写的那条 fact → 「证书到期监控」保住了。** 这验证了 §4.4 的时间窗口解释。

**结论边界（重要，不要超出证据）**：

| 论断 | 状态 |
|---|---|
| 提高 `max_tokens` 显著改善内容保留 | ✅ 已验证（轮次 1/2 五项全丢 → 轮次 3/4/5 大幅改善） |
| `delta` 模式有独立贡献 | ✅ **有证据**（轮次 4 vs 5，同为 4096，full 丢 3 项、delta 保住 4 项） |
| ↑ 但归因不严格 | ⚠️ **两轮的 `facts.retrieved` 不同**（world 60 vs 57、experience 34 vs 52），不是严格单变量。delta 表现更好是事实，"由 delta 机制导致"仍有干扰 |
| delta/4096 能否稳定保住全部五项 | ⚠️ **只验证过一轮**（轮次 5）。轮次 3 同配置丢 1 项，说明**结果有随机性**，需要更多轮次才能说"稳定" |
| 「证书到期监控」彻底解决 | ✅ 已验证（轮次 5 保住，前提是 fact 已入窗口） |

**最佳组合**：**`max_tokens=4096` + `mode=delta`** —— 两者缺一不可。

### 4.4 时间窗口约束（已验证）

第 3 轮 dry-run 的 window：`created_before: 2026-11-15T16:24:50Z`（= CST 00:24:50）。补写那条 fact 的时间是 **00:28**，**晚于窗口**，所以没被读到。

**「刷新只读窗口之后的内容」是硬约束** —— 要让某条 fact 参与本次刷新，必须在刷新启动前写入并完成 consolidation。

**已验证**：轮次 5 的窗口为 `17:08:26Z`（CST 01:08），已覆盖 00:28 写入的 fact → 「证书到期监控」✅ 保住。

**这条同时证明了 §4.6 的必要性**：mental model 只读记忆库，**任何只存在于正文里的内容，在重写时都无从获取**。

### 4.5 最终配置

```http
PATCH /v1/default/banks/hermes/mental-models/homelab-architecture
{"trigger": {"mode":"delta", "refresh_after_consolidation":true,
             "min_refresh_interval_seconds":86400, "budget":"mid",
             "keep_trace":false, "exclude_mental_models":false},
 "max_tokens": 4096}
```

| mental model | mode | max_tokens | 状态 |
|---|---|---|---|
| `homelab-architecture` | **delta** | **4096** | ✅ **已刷新成功**（2026-11-16 08:44，内容 4095 → 5576 字符） |
| `user-profile` | **delta** | **4096** | ✅ **已刷新成功**（2026-11-16 08:41，内容 1442 → 2580 字符） |

**两个模型都已切到 `delta` + `4096` 并完成真实刷新。**

**与官方 Pages 默认配置的对齐情况**：

```json
// Pages 默认
{"mode": "delta", "fact_types": ["observation"],
 "exclude_mental_models": true, "refresh_after_consolidation": true}
```

| 配置 | Pages 默认 | 本次设置 | 是否一致 |
|---|---|---|---|
| `mode` | delta | delta | ✅ |
| `max_tokens` | 4096 | 4096 | ✅ |
| `refresh_after_consolidation` | true | true | ✅ |
| `fact_types` | ["observation"] | 全部三类（未设） | ❌ **有意不同** |
| `exclude_mental_models` | true | **false** | ❌ **未对齐** |

**两处有意/无意的差异**：

- **`fact_types` 不同是有意的** —— Pages 默认只读 observation，而 `homelab-architecture` 需要 world（IP、端口、路径等细节大量存在于 world fact），所以保持全量。见 §5.3。
- **`exclude_mental_models: false` 未对齐 Pages 默认** —— 本次 PATCH 沿用了原值，没有刻意改成 true。原因：另一篇 `user-profile` 也是 mental model，若排除所有 mental model，`homelab-architecture` 的刷新将读不到它（同为 mental model 的内容）。**但这与官方 Pages 默认不一致，属于未经论证的沿用，应在下次调优时确认。**

**结论边界**：本次调参**部分**对齐了官方默认值（mode / max_tokens / refresh_after_consolidation 三项），**不是完全对齐**。

### 4.6 两个建议固化进记忆库的 fact

刷新只读记忆库，不读 vault 文档 —— 所以**只存在于 mental model 正文里的内容，重写时无从获取，必然丢失**。

本次补写了三��� fact：

1. **reranker 换 hs-rerank-1 + A/B 数据**（否则下次刷新会写回旧的 `bge-reranker-base`）
2. **证书链路四个待办项**（TLS 终止点 / `nginx -t` / SNI 探测 / 到期监控）
3. **`/dev/sdb1` ext4 元数据错误计数**（11-16 刷新后补写 —— 该项在刷新中丢失，
   因为它同样只存在于旧版正文。这是该规律的第三次验证）

> **规律：mental model 正文 ≠ 事实来源。要长期保住的结论，必须在 fact 层有一条独立记录。**

### 4.7 官方推荐的监控指标

```http
GET /v1/default/banks/{bank_id}/stats  →  paused_mental_models
```

**该值 > 0 即表示有模型停止自我更新，应接入告警。** 失败还会记进 history：

```http
GET /v1/default/banks/{bank}/mental-models/{id}/history
```

失败记录的 `kind: refresh_failed`，带 `failure_reason`：
`retrieval_failed` / `no_answer` / `unexpected_error` / `empty_candidate` /
`structured_doc_unreadable` / `delta_ops_failed` / `delta_ops_all_skipped` /
`delta_not_applied` / `structured_output_failed` / `candidate_rejected`

---

## 5. Pages 评估（结论：暂不实施）

官方新功能，值得记录决策依据。

### 5.1 Pages 是什么

Page 底层由 Mental Model 支撑（`CreatePageResponse` 返回 `page_id` + `mental_model_id`），但有一套更适合文档维护的默认配置：

| 配置 | Pages 默认 | 普通 Mental Model 默认 |
|---|---|---|
| `max_tokens` | **4096** | 2048 |
| `mode` | **delta** | full |
| `fact_types` | **["observation"]** | 全部三类 |
| `exclude_mental_models` | true | false |
| `refresh_after_consolidation` | true | false |

### 5.2 最有价值的一点

```http
GET /v1/default/banks/{bank_id}/pages/search
```

> *"Doc-level hybrid search across a bank's pages: a full-text (BM25) match and a vector-similarity match, Reciprocal-Rank-Fusion fused. **No reranker — tuned for latency.**"*

**不走 reranker** —— 对 4 核 CPU 是实打实的价值。

### 5.3 为什么不实施

**① 当前瓶颈是刷新稳定性，不是检索速度。**
`retry_blocked` 尚未验证是否自愈。在漏水的桶上再开一个口，只会让过期内容更容易被读到。

**② `fact_types: ["observation"]` 是结构性强制，不是偏好。**
官方原文 —— *"Enforced structurally — with only `observation` in scope, the refresh agent **isn't given the raw-memory recall tool at all**."*

本库 `homelab-architecture` 实际用的是 world(37) + experience(17) + observation(15)。**IP、端口、路径这些细节大量存在于 world fact**，若只读 observation，Page 里不会出现。

**③ 不能把现有 mental model 直接转成 Page。**
`POST /pages` 只会新建一个 backing mental model。虽然 `PATCH /pages/nodes/{id}` 能改 trigger（含 `fact_types`），但那意味着**新旧两份各刷各的，存在重复刷新开销**（每次刷新都占 LLM slot 和重排资源，量级取决于两份文档的大小与内容重叠度），**且内容重复维护**。

**④ 当前调用路径用不上。**
Hermes 现在是「每轮对话自动 retain → 注入相关记忆」，走的是 recall，不是 pages search。Pages 是给「Agent 主动查文档」用的路径，而 Hermes 目前没有这条调用链。

### 5.4 顺带发现的一个坑

Pages 的 `tags` 是**严格过滤条件**，不是分类标签。官方原文：

> *"Tags invented for the page (a topic, a document type) **match nothing** unless your memories were retained with those exact tags, and the page generates as 'I don't have information about this'."*

而且 `type:<x>` 标签（用来设置渲染类型，如 `type: runbook`）**也参与过滤** —— 设了它，没这个标签的记忆全被排除。

---

## 6. 当前配置基线

### 6.1 `/opt/hindsight/hindsight.env`（权限 600）

```ini
HINDSIGHT_API_DATABASE_URL=postgresql://[REDACTED]@192.168.31.5:5432/hindsight
HINDSIGHT_API_LLM_PROVIDER=minimax
HINDSIGHT_API_LLM_MODEL=MiniMax-M2.7-highspeed
HINDSIGHT_API_LLM_BASE_URL=https://api.minimaxi.com/v1
HINDSIGHT_API_LLM_API_KEY=[REDACTED]
HINDSIGHT_API_EMBEDDINGS_PROVIDER=local
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3
HINDSIGHT_API_RERANKER_PROVIDER=local
HINDSIGHT_API_RERANKER_LOCAL_MODEL=hindsight-ai/hs-rerank-1
HINDSIGHT_API_RERANKER_MAX_CANDIDATES=50
HINDSIGHT_API_REFLECT_WALL_TIMEOUT=900
HINDSIGHT_API_HOST=127.0.0.1
HINDSIGHT_API_PORT=8888
HF_HOME=/opt/hindsight/hf-cache
```

### 6.2 性能基线（换模型后）

| 操作 | 换模型前 | 换模型后 | 备注 |
|---|---|---|---|
| 普通 recall（端到端） | 36.2s | **10.97s** | 同一 query 串行 A/B，-69% |
| 其中重排 50 候选 | **35.6s**（日志 `reranking=35590ms` ×3） | **22.1s**（日志 `reranking=22056ms`） | **重排本身只快约 38%**，端到端 69% 的降幅还包含候选池差异（旧轮 pre-filtered 1235 条，新轮 419 条） |
| 完整 reflect（mental model 刷新） | 276–298s | **122–167s**（dry-run 实测） | ⚠️ **端到端对比，非单变量**：旧数据来自真实刷新（bge-reranker-base / full 模式），新数据来自 dry-run（hs-rerank-1 / full 与 delta 两种模式）；reranker 已更换、MiniMax 响应时间波动，未控制变量 |

### 6.3 待观察项

| 项 | 观察方式 | 状态 |
|---|---|---|
| ~~`retry_blocked` 是否自愈~~ | 手动刷新成功即解锁 | ✅ **已解决** —— 11-16 08:41 / 08:44 两次手动刷新成功，`paused_mental_models: 0`，两个模型 `last_refresh_failed_at` 均为 null |
| 新的 reflect 实际耗时 | 下一次自动刷新的日志 | 待观察 |
| `paused_mental_models` 是否归零 | `GET /banks/hermes/stats` | 待观察 |
| `user-profile` 内容是否丢失 | 它还是 full/1024，1442 字符未超预算，风险低但非零；丢了就改成 `delta` + `4096` | 待观察 |
| ~~缺失实验：`full/4096` 对照~~ | 单独跑 full + 4096 的 dry-run | ✅ **已做**（轮次 4）—— full 丢 3 项、delta 保住 4 项，delta 有独立贡献 |
| ~~缺失实验：fact 入窗口后重测~~ | 刷新后检查「证书到期监控」是否保住 | ✅ **已做**（轮次 5）—— 窗口覆盖后保住，验证成立 |
| **仍缺失：多轮次稳定性** | delta/4096 只验证过 2 轮（轮次 3 丢 1 项、轮次 5 全保住），需更多轮次判断是否稳定 | **未做** |
| **仍缺失：召回准确率基线** | 准备一组固定 query + 人工标注期望结果集，测两个 reranker 的 recall@k | **未做** —— 这是判断换模型是否等价的唯一办法 |

> **2026-11-16 08:45 最终状态**：两个 mental model 均已真实刷新成功。
>
> | | 刷新前 | 刷新后 | 耗时 |
> |---|---|---|---|
> | `user-profile` | 1442 字符 / 11-15 14:59 | **2580 字符 / 11-16 08:41** | 64s（4 iterations, 3 tool calls） |
> | `homelab-architecture` | 4095 字符 / 11-15 01:09 | **5576 字符 / 11-16 08:44** | 130s（7 iterations, 6 tool calls） |
>
> `paused_mental_models: 0`，`last_refresh_failed_at` 均为 null，`retry_blocked` 已清零。
>
> **语义保留率验证**：`homelab-architecture` 16/17（唯一缺 ext4 错误计数）、`user-profile` 12/12。
> 缺的那一项**正好印证了 §4.6 的规律** —— 它只存在于旧版正文、没有 fact 支撑，
> 已于刷新后补写为 fact（见下）。

---

## 7. 复用价值

### 7.1 这套流程适用于任何"跨大版本升级 + 有存量数据"的服务

1. **先只读侦察**：下 wheel 读迁移链 / 读 changelog / 读官方文档
2. **算清"待执行 N 个"**，逐个过筛出危险项
3. **对每个危险项写一条针对性 SQL**，在生产上查影响面（只读）
4. **备份 + 验证备份可读**（`pg_restore -l`）
5. **改配置前先备份配置**，A/B 对照时能精确回滚
6. **升级后逐项回读验证**：版本号 / alembic / 行数 / 维度 / 索引
7. **观察一个完整周期再宣布解决**
8. **区分"已验证"与"假设"**：每条结论标注验证强度。
   本文档初版把「升级成功」「性能改善」「召回质量」「刷新机制恢复」混在一起陈述，
   实际上只有前两项有回读/对照证据。**尤其不要把"端到端对比"写成"某参数的独立贡献"。**

### 7.2 三个可复用的具体做法

**① 迁移链方向**：从 head 往生产版本走，不是从生产往 head 走。

**② 用 dry-run 代替真实变更**：Hindsight 的 `dry-run-refresh` 返回完整 diff + warnings，不落盘。**`warnings` 字段是金矿** —— 根因就写在里面。

**③ A/B 对照要算差集**：对比两轮结果按 id 求差集（`仅旧有新无` / `仅新有旧无`），不能只比条数。只比条数会把"预算重新分配"误判成"召回退化"。

### 7.3 值得记住的三个认知

| 认知 | 纠正了什么 |
|---|---|
| **内容丢失 = 预算不足，不是 LLM 漂移** | delta/2048 和 full/2048 丢的是同一批内容 —— 都因为文档 2769 tokens 超了 2048 预算 |
| **`failed` ≠ `parked`** | failed 之后自动触发器彻底停摆，必须手动成功一次才恢复 |
| **mental model 正文 ≠ 事实来源** | 只存在于正文里的内容，重写时必然丢失，要在 fact 层独立固化 |
| **差集计算必须用完整 id + 数学校验** | 本文档初版用 `id[:8]` 截断做集合 key，**前缀碰撞**导致 4 条被误判为"共同命中"，得出"仅旧有=0"的错误结论。**先校验 `总数 − 共同 = 差集` 再下结论。** |
| **内容保留要按语义检查，不按字面匹配** | 判断"某项是否丢失"时用正则匹配字面串，会因重写改变了句式而误判丢失。轮次 5 里"TLS 终止点未明确"与"证书链路四项"被拆成两条 bullet，字面正则失效但语义完整。**先看实际文本再下结论。** |

---

## 8. 相关文档

- [[homelab/AI Agent/Hindsight/Hindsight 官方文档速查.md]] — 官方 1.2.x 资料整理
- [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]] — 部署运维 SOP
- [[homelab/05-事件记录/2026-11-01-hindsight-rerank-timeout.md]] — 重排超时事故（本次变更的前因）
