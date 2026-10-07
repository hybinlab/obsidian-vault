---
publish: true
---

对应部署已经跑起来的 [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]]，这篇整理 Hindsight 的 Bank Template 功能——用一份 JSON 清单，一次 API 调用就能把一个 bank（记忆库）的配置、心理模型、指令全部配好，不用在 Web UI 里一项项手动点。

## 是什么、解决什么问题

Bank Template 是声明式的 JSON 配置清单，导入时会创建或更新对应的 bank；反过来也能把一个已经调好的 bank 导出成模板。典型用途：

- **复制**：给多个用户/agent 快速生成同一套配置的 bank
- **入职**：新用户直接拿到验证过的配置，不用从零摸索
- **分享**：把调好的配置当成可移植 JSON 文件分发
- **框架集成**：集成方案里随包分发推荐模板

## 顶层字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `version` | 是 | 架构版本，当前是 `"1"` |
| `bank` | 否 | bank 配置覆盖项 |
| `mental_models` | 否 | 心理模型定义（数组） |
| `directives` | 否 | 指令定义（数组） |

## `bank` 配置字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `reflect_mission` | string | — | 反思（reflect）操作的任务/上下文 |
| `retain_mission` | string | — | 指导"提取什么内容"进记忆 |
| `retain_extraction_mode` | string | — | 提取模式：`concise`/`verbose`/`custom`/`verbatim`/`chunks` |
| `retain_custom_instructions` | string | — | 自定义提取提示词，`retain_extraction_mode = custom` 时才需要 |
| `retain_chunk_size` | integer | — | 内容块目标最大字符数 |
| `retain_structured_chunk_size` | integer | 继承 `retain_chunk_size` | 单条 JSONL 行/单轮对话的最大字符数 |
| `disposition_skepticism` | integer 1-5 | — | 怀疑程度——越高越倾向质疑输入内容 |
| `disposition_literalism` | integer 1-5 | — | 字面理解程度——越高越倾向照字面意思理解，不做引申 |
| `disposition_empathy` | integer 1-5 | — | 共情程度 |
| `enable_observations` | boolean | — | 是否启用"观察整合"功能 |
| `observations_mission` | string | — | 观察整合的合成方向/控制指导 |
| `entity_labels` | object[] | — | 受控词汇表的标签组，约束实体识别范围 |
| `entities_allow_free_form` | boolean | — | 是否允许识别词汇表之外的自由格式实体 |

`disposition_*` 这三个是 Hindsight 的"性格旋钮"，控制模型处理记忆时的态度倾向，1-5 分档，配合部署 SOP 里"中英混合"的场景，值得按实际语料调一调，默认值官方文档没写死。

## `mental_models` 字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 唯一标识，小写字母数字和连字符 |
| `name` | 是 | 可读名称 |
| `source_query` | 是 | 生成这个心理模型内容用的查询 |
| `tags` | 否 | 可见性标签，默认 `[]` |
| `max_tokens` | 否 | 256–8192，默认 2048 |
| `trigger` | 否 | 自动刷新的触发设置 |

**按 `id` 匹配更新**：重复导入同一个 `id` 的心理模型会覆盖更新，不会产生重复项。

## `directives` 字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` | 是 | 指令名称，**重复导入时按这个字段匹配更新** |
| `content` | 是 | 指令正文 |
| `priority` | 否 | 优先级，默认 `0` |
| `is_active` | 否 | 是否激活，默认 `true` |
| `tags` | 否 | 分类标签，默认 `[]` |

## 完整示例

```json
{
  "version": "1",
  "bank": {
    "retain_mission": "Extract customer issues, resolutions, and sentiment.",
    "enable_observations": true,
    "observations_mission": "Track recurring customer pain points."
  },
  "mental_models": [
    {
      "id": "sentiment-overview",
      "name": "Customer Sentiment Overview",
      "source_query": "What is the overall sentiment trend?",
      "trigger": { "refresh_after_consolidation": true }
    }
  ],
  "directives": [
    {
      "name": "Acknowledge frustration",
      "content": "Always acknowledge frustration before offering solutions.",
      "priority": 10
    }
  ]
}
```

## 其他特性

- **干运行（dry run）**：支持只验证不应用，改配置前先跑一遍看有没有问题
- **导出再导入**：可以把调好的 bank 导出成模板，再导入到另一个 bank，实现配置轮转/复制
- **版本自动升级**：旧版本的清单导入时会自动升级到当前架构版本

## 相关笔记

- [[homelab/AI Agent/Hermes + Hindsight（Bare Metal）部署 SOP.md]] — 部署、环境变量、踩坑记录
- [[homelab/AI Agent/Hindsight/Hindsight Memories API.md]] — 记忆单元的管理操作（编辑/失效）
- [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]] — Bank 本身的概念、这些配置字段实际控制什么阶段
