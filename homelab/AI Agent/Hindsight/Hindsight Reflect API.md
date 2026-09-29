---
publish: true
---

对应 [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]] 里提到的 Reflect 阶段（`reflect_mission`/disposition 那组配置），这篇展开 Reflect 这个操作本身——请求参数、响应结构、失败行为。

## Reflect 是什么，跟 Recall/Retain 有什么区别

三个操作分工完全不同：

| 操作 | 干什么 | 输出 |
| --- | --- | --- |
| **Retain** | 存记忆 | 无（存储动作，不返回内容） |
| **Recall** | 检索原始事实 | 结构化的事实列表，原样返回 |
| **Reflect** | 跑一个**自主代理循环**，搜索记忆库、套用 bank 的 disposition 塑造推理风格 | LLM **合成**出来的一段 markdown 答案 |

一句话区分：Recall 是"查表"，Reflect 是"想清楚再回答"——跑多轮工具调用、多个检索源交叉验证，产出的是深思熟虑的答案，不是原始数据堆砌，适合招聘决策、政策咨询这类需要综合判断的场景。

## 请求参数

### `query`（必填，唯一必填字段）

```python
client.reflect(bank_id="my-bank", query="What should I know about Alice?")
```

有上下文信息直接写进 query 里，不用单独传。

### `budget`（可选，默认 `low`）

控制代理探索深度：`low`（浅层搜索，优化速度）/ `mid` / `high`（深度探索，跨所有知识层级）。

```python
response = client.reflect(
    bank_id="my-bank",
    query="We're considering a hybrid work policy. What do you think about remote work?",
    budget="mid",
)
```

### `max_tokens`（可选，默认 `4096`）

限制**最终生成答案**的长度，**不影响代理检索能力**——检索该跑多深还是多深，只是最后憋出来的答案字数受限。

### `response_schema`（可选）：结构化输出

代理先正常推理出答案，再跑第二遍把答案提取成符合 JSON Schema 的结构化对象：

```python
from pydantic import BaseModel

class HiringRecommendation(BaseModel):
    recommendation: str
    confidence: str  # "low", "medium", "high"
    key_factors: list[str]
    risks: list[str] = []

response = client.reflect(
    bank_id="hiring-team",
    query="Should we hire Alice for the ML team lead position?",
    response_schema=HiringRecommendation.model_json_schema(),
)

result = HiringRecommendation.model_validate(response.structured_output)
```

**`structured_output` 是 `text` 的忠实映射，不是替代品**——即使给了 `response_schema`，`text` 这个可读的 markdown 答案照样返回，两者同时给你：人看的答案 + 程序能解析的类型化对象。

### `tags`（可选）：限定检索范围

过滤代理能检索到的事实/观察/心智模型/指令范围：

| 配置 | 事实/观察 | 心智模型 | 指令 |
| --- | --- | --- | --- |
| 不传（或 `tags: []`） | 全部 | 全部 | 仅全局指令 |
| `tags_match: "exact"` | 仅全局 | 仅全局 | 仅全局 |
| 非空 `tags` + `any`/`all` | 匹配的 + 全局 | 匹配的 + 全局 | 匹配的 + 全局 |
| 非空 `tags` + `*_strict` | 仅匹配的（排除无标签数据） | 仅匹配的 | 匹配的 + 全局 |
| 非空 `tags` + `exact` | 精确匹配这个标签集合 | 精确匹配 | 精确匹配 + 全局 |

```python
response = client.reflect(
    bank_id="my-bank",
    query="What does this user think about our product?",
    tags=["user:alice"],
    tags_match="any_strict",
)
```

**指令（Directive）有个特殊规则**：不管 `tags` 怎么设，**全局（无标签）指令永远生效**——这是 Directive 作为"硬性规则"的设计意图，不应该因为查询范围窄了就被绕开。

### `tag_groups`（可选，跟 `tags` 互斥）

复合标签过滤，支持递归 `and`/`or`/`not` 表达式，比单纯 `tags` 更灵活，每个叶子节点默认 `any_strict`，顶层组之间是 AND。简单场景用 `tags` 就够，需要复杂布尔组合才用这个。

### `include`：要不要返回额外的调试/审计信息

**`include.facts`**：响应里加一个 `based_on` 对象，列出代理实际用了哪些记忆/心智模型/指令——只有真被检索用到的才会出现，用来做透明度审计、验证答案有没有依据：

```python
response = client.reflect(bank_id="my-bank", query="Tell me about Alice", include_facts=True)
print("Response:", response.text)
for fact in (response.based_on.memories if response.based_on else []):
    print(f"  - [{fact.type}] {fact.text}")
```

**`include.tool_calls`**：响应里加一个 `trace` 对象，记录代理循环里每一次工具调用和 LLM 调用的完整日志（输入、输出、耗时）——纯调试用，设 `output: false` 能只保留输入、减小载荷体积。

### 两个精细控制项（一般用默认值就够）

- `reflect_search_observations_max_tokens`（默认 `5000`）：`search_observations` 这个工具的 token 预算，观察类证据往往是大 bank 上下文里占比最大的部分，调小能换取更快更小的 LLM 上下文
- `reflect_search_observations_include_entities`（默认 `true`）：是否给每条观察附加解析出来的实体名，表面文本用别名时有用，但可能占掉序列化载荷一半以上，不需要就关掉

这两个也能在 bank 级别通过 `reflect_default_options` 配置成默认值（见 [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]]），单次请求显式传的值优先级最高。

## 响应结构

| 字段 | 何时出现 | 内容 |
| --- | --- | --- |
| `text` | 总是 | 合成答案，markdown 格式，**主要输出** |
| `structured_output` | 传了 `response_schema` 且提取成功 | 按 schema 解析出的结构化对象 |
| `structured_output_error` | 传了 `response_schema` 但提取阶段失败（供应商报错/超时/解析不了） | **Reflect 本身仍算成功**（照样返回 200 + `text`），这个字段只说明"为什么拿不到结构化那部分" |
| `based_on` | `include.facts=true` | 实际用到的 memories/mental_models/directives |
| `usage` | 总是 | `input_tokens`/`output_tokens`/`total_tokens`，整个代理循环所有 LLM 调用的加总 |
| `trace` | `include.tool_calls=true` | 完整执行日志，`tool_calls`（每次工具调用）+ `llm_calls`（每次 LLM 调用，含 `scope` 和耗时） |

**注意区分**：`structured_output` 缺失且没有 `structured_output_error` 是正常情况（没传 schema，字段直接省略）；`structured_output_error` 这个字段**存在**才是需要关注的信号——说明结构化提取本该发生但失败了，值得重试或者告警。

## 跟 disposition / Directive / Mental Model 的关系

- **disposition**（`disposition_skepticism`/`disposition_literalism`/`disposition_empathy`，见 [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]]）：塑造推理**风格**，同一个 query 在不同 disposition 的 bank 下会得到风格不同的答案
- **Directive**：被注入进 reflect 的 prompt 里引导代理行为，全局指令永远生效，打标签的按 `tags` 范围生效
- **Mental Model**：代理可以检索、套用已经存好的心智模型（组织沉淀下来的知识/决策框架），跟 Directive 是互补关系——Directive 管"必须怎么做"，Mental Model 提供"可以参考的框架"

## 失败行为：宁可报错，不要给空答案

Reflect 收集不到证据时**返回 500，而不是憋一个空答案出来**，触发条件：

- 检索工具本身挂了（数据库/嵌入器/重排器不可用）
- 模型没生成出任何答案
- 模型没法正确驱动工具调用（reflect 完全靠结构化工具调用驱动）
- 供应商持续报错（非上下文溢出类错误，重试一次后放弃）

**两种情况故意不算失败**：
- 上下文窗口溢出——从已有证据里凑合成答案（预算不够是预算问题，不是失败）
- 模型工具调用参数错了——把错误信息返回给模型自己纠正，不直接抛出异常

**"检索到但内容为空"不是失败**——如果 bank 里确实没有相关内容，reflect 会在答案里如实说"没有相关信息"，这跟"系统出错了"是两回事，别把这两种情况混着处理重试逻辑。

## 典型场景

| 场景 | 用法 |
| --- | --- |
| 招聘决策 | `response_schema` 提取 recommendation/confidence/key_factors/risks |
| 复杂政策咨询 | `budget="high"` 深度探索 |
| 按用户做反馈分析 | `tags=["user:alice"]` 限定范围 |
| 答案可信度审计 | `include_facts=true` 看引用源 |
| 调试代理推理过程 | `include.tool_calls=true` 看完整执行轨迹 |

## 相关笔记

- [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]] — disposition/reflect_mission 等配置字段
- [[homelab/AI Agent/Hindsight/Hindsight Memories API.md]] — Reflect 检索到的记忆单元本身怎么管理
- [[homelab/AI Agent/Hermes + Hindsight 部署 SOP.md]] — 部署
