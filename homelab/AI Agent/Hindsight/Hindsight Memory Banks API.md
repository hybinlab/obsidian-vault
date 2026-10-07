---
publish: true
---

Bank 是 Hindsight 里最核心的概念，[[homelab/AI Agent/Hindsight/Hindsight Bank Templates.md]]（配置模板）和 [[homelab/AI Agent/Hindsight/Hindsight Memories API.md]]（记忆单元）都是围绕 Bank 转的，这篇把 Bank 本身讲清楚，算是 Hindsight 概念体系的中心节点。

## Bank 是什么

一个 memory bank 是**完整、隔离的存储单元**，包含五样东西：

| 组成 | 内容 |
| --- | --- |
| Memories | 事实信息（对应 [[homelab/AI Agent/Hindsight/Hindsight Memories API.md]] 讲的 World/Experience/Observation） |
| Documents | 原始文件内容 |
| Entities | 人物/地点/概念 |
| Relationships | 知识图谱里的连接关系 |
| Directives | 硬性规则 |

**完全隔离**：一个 bank 里的记忆对其他 bank 不可见，天然做多租户/多 agent 隔离。**自动创建**：写操作第一次碰到不存在的 bank 会自动建，不需要预先创建；但**只读**操作碰到不存在的 bank 返回 404，不会自动建（这个区别容易踩坑——以为"读一下试试"会自动初始化，实际上读操作不会）。

## 四类配置字段

Bank 的行为配置分四组，对应四种不同的操作阶段：

### Retain（提取）

| 字段 | 说明 |
| --- | --- |
| `retain_mission` | 纯文本指导，告诉系统"提取时关注什么"，比如"包含技术决策和架构权衡，忽略会议后勤" |
| `retain_extraction_mode` | 提取激进程度：`concise`（默认）/`verbose`/`custom`/`verbatim`/`chunks` |
| `retain_chunk_size` | 分块大小，字符数，默认 3000——调大减少 LLM 调用次数但可能降低提取质量 |
| `entity_labels` | 受控词汇的标签分类，参与知识图谱链接和检索 |

### Observations（观察整合）

| 字段 | 说明 |
| --- | --- |
| `enable_observations` | 开关 |
| `enable_auto_consolidation` | 自动巩固还是只能手动触发 |
| `observations_mission` | 定义"什么该被合成为持久观察" |
| `consolidation_llm_batch_size` | 每次 LLM 调用处理的事实数量 |

### Reflect（反思）

| 字段 | 说明 | 取值范围 |
| --- | --- | --- |
| `reflect_mission` | 第一人称身份/推理框架 | — |
| `disposition_skepticism` | 评估陈述时的怀疑程度 | 1-5（1=信任，5=怀疑） |
| `disposition_literalism` | 字面理解程度 | 1-5（1=灵活，5=严格） |
| `disposition_empathy` | 情感背景的权重 | 1-5（1=冷漠，5=共情） |

这几个跟 [[homelab/AI Agent/Hindsight/Hindsight Bank Templates.md]] 里列的字段是同一套，那篇是"怎么打包进模板批量下发"，这篇是"这些字段实际控制什么阶段的行为"。

### Recall（检索）

`recall_budget_function` 控制检索广度怎么映射：
- `fixed`（默认）：检索预算固定，跟输出大小无关
- `adaptive`：检索预算跟 `max_tokens` 成比例缩放

## 操作端点（以 Python 为例，Node/Go/CLI 语法结构一致）

### 创建 Bank

```python
client.create_bank(bank_id="my-bank")
```

### 更新配置

```python
client.update_bank_config(
    "my-bank",
    retain_mission="Always include technical decisions...",
    retain_extraction_mode="verbose",
    disposition_skepticism=4,
    disposition_literalism=4,
    disposition_empathy=2
)
```

### 查询配置

```python
data = client.get_bank_config("my-bank")
# data["config"]    — 完整解析后的配置（服务器默认 + bank 覆盖 合并结果）
# data["overrides"] — 仅这个 bank 自己覆盖了哪些字段
```

**分层覆盖模型**：配置分两层，服务器默认值打底，bank 级配置在上面覆盖，`get_bank_config` 一次返回两层，方便区分"这是继承来的默认值"还是"这是这个 bank 专门设的"。

### 重置为服务器默认

```python
client.reset_bank_config("my-bank")
```

## Directives：硬性规则，跟 disposition 不是一回事

容易搞混的两个概念：

- **disposition**（上面 Reflect 里那几个 1-5 分档）：**软性**的推理风格倾向，影响"模型怎么想"
- **Directive**：**硬性**规则，必须严格执行，比如"永不分享个人数据"

```python
directive = client.create_directive(
    bank_id=BANK_ID,
    name="Formal Language",
    content="Always respond in formal English..."
)

directives = client.list_directives(bank_id=BANK_ID)

# 禁用而不是删除
client.update_directive(bank_id=BANK_ID, directive_id=directive_id, is_active=False)

client.delete_directive(bank_id=BANK_ID, directive_id=directive_id)
```

**标签范围**：不打标签的 Directive，每次 reflect 都生效；打了标签的，只在 reflect 请求带上匹配标签时才生效；请求里加 `apply_all_directives=true` 可以无视标签范围，强制所有 Directive 一起生效。

## Bank 转移：导出 / 导入 / 克隆

三种操作，用途不同：

**导出**（后台异步操作，提交后轮询，完成后下载 ZIP）：

```python
archive = await client.aexport_bank("transfer-py")

# 只导出记忆数据，不带配置
memories_only = await client.aexport_bank("transfer-py", include_bank_config=False)
```

导出内容用三个开关控制：
- `include_data`：文档、提取的事实、观察、Mental Models
- `include_bank_config`：配置、Directives、Webhooks
- `include_history`：审计日志和 LLM 请求记录

**导入**有两种模式：

```python
# restore：整个 bank 搬到一个新 bank_id（目标必须不存在）
operation_id = await client.aimport_bank("transfer-py", archive, target_bank_id="transfer-py-copy")

# merge：文档合并进已存在的 bank，冲突时按 document_conflict 处理（skip/replace/new-id）
submission = await client.bank_transfer.import_bank_transfer(
    "transfer-py-other",
    ("transfer-py.zip", archive),
    mode="merge",
    document_conflict="replace"
)
```

**克隆**——一步到位，不用手动导出再导入：

```python
operation_id = await client.aclone_bank("transfer-py", "transfer-py-clone")
```

**导出/导入/克隆全程不调用 LLM**，原始文本原样保留，只在目标 bank 里重新做 embedding、重新解析实体——这意味着搬迁数据不产生额外的 LLM 调用费用，但也意味着如果目标 bank 的 `retain_mission` 跟源 bank 不一样，搬过去的内容不会按新 mission 重新提取，还是原来提取时的老结果。

## Prompt Preview：看 LLM 实际会收到什么，不真的调用

调试 `retain_mission`/`reflect_mission` 这些文本指导到底会怎么拼进最终发给 LLM 的 prompt 里，不用真跑一次浪费 token：

```python
from hindsight_client_api.models import PromptPreviewRequest
preview = await client.banks.preview_prompt("my-bank", PromptPreviewRequest(operation="retain"))
for message in preview.messages:
    print(message.role, len(message.blocks))
```

返回结构能看到每个 prompt block 是内置的（`source: builtin`）还是来自你配置的字段（`field: retain_extraction_mode`），以及是否可编辑——调 mission 文案时，先用这个看效果，比直接跑真实数据划算。

## Memory Defense：per-bank 安全策略

控制敏感数据怎么处理：

```json
{
    "memory_defense": {
        "enabled": true,
        "default_action": "redact",
        "protected_tag_namespaces": ["pii"],
        "rules": [
            { "on": "prompt_injection", "action": "block", "min_severity": "high" }
        ]
    }
}
```

`default_action` 四选一：`allow`/`redact`（脱敏）/`quarantine`（隔离待审）/`block`（直接拒绝）。对应部署 SOP [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]] §14 安全那节提到的"REST API 默认无鉴权"，这个 Memory Defense 是内容层面的防护，跟网络层面的访问控制是两回事，两个都要配才算完整。

## 小结

Bank 是容器，四组配置（retain/observations/reflect/recall）控制四个不同阶段的行为，Directive 是硬性规则、跟软性的 disposition 分开管理，导出/导入/克隆全程不耗 LLM token，Prompt Preview 能在不调用 LLM 的情况下预览最终 prompt，Memory Defense 管内容层面的安全。

## 相关笔记

- [[homelab/AI Agent/Hindsight/Hindsight Bank Templates.md]] — 把这些配置打包成模板批量下发
- [[homelab/AI Agent/Hindsight/Hindsight Memories API.md]] — Bank 里存的记忆单元怎么管理
- [[homelab/AI Agent/Hindsight/Hindsight Reflect API.md]] — Reflect 操作详解（请求参数、响应结构、失败行为）
- [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]] — 部署、安全配置
