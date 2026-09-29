---
publish: true
---

对应 [[homelab/AI Agent/Hermes + Hindsight 部署 SOP.md]] §9 冒烟测试里用到的 `/v1/default/banks/test/memories` 那套接口，这篇整理 Memory（记忆单元）的概念和管理操作，重点是官方 "When to reach for what" 那节——遇到记忆错了/过时了，该用哪个操作。

## Memory Unit 是什么

Hindsight 提取、存储的原子级事实，按来源分三类：

| 类型 | 含义 |
| --- | --- |
| **World** | 世界状态类事实 |
| **Experience** | 用户经历类事实 |
| **Observation** | 从 World/Experience 派生出来的观察结论 |

状态只有两种：`valid`（有效）、`invalidated`（已失效，不是物理删除）。

**关键限制**：只有 **World** 和 **Experience** 能被手动管理（编辑/失效）；**Observation** 是派生出来的，会跟着源事实自动重新生成，**不能直接编辑**——想改 Observation 的内容，得改它依赖的源事实或者调 `observations_mission`。

## 操作端点

| 方法 | 端点 | 作用 |
| --- | --- | --- |
| GET | `/memories/list` | 列表/筛选记忆单元 |
| GET | `/memories/{id}` | 查单条 |
| GET | `/memories/{id}/history` | 看派生观察的刷新历史 |
| PATCH | `/memories/{id}` | 编辑 / 失效 / 恢复 |
| DELETE | `/memories/{id}/observations` | 清除某条记忆派生出的观察 |

## When to reach for what：该用哪个操作

| 场景 | 该做什么 | 为什么 |
| --- | --- | --- |
| **整个 bank 提取方式系统性错了** | 改 `retain_mission`/`observations_mission`，然后**重新处理文档** | 系统性问题在源头修，重新跑一遍，不要一条条改 |
| **单次误提取**（个别记忆内容错了） | **编辑**这条记忆 | 更正事实，相关的派生内容会自动重新生成 |
| **事实已经过时、且没有新事实替代** | **失效**这条记忆 | 明确告诉系统"这个世界状态已经变了" |
| **重复记忆，或者已经被别的记忆取代** | **失效**旧的那条 | 清掉噪音，同时保留审计线索（不是删除） |
| **新事实已经存进去，覆盖了旧事实** | 什么都不用做，只留新事实 | 巩固（consolidation）过程本身已经在流水线里处理过矛盾了 |

**判断口诀**：**"Hindsight 本来就该知道的，交给巩固机制自己处理；只有你自己知道的事，才需要你手动管理。"**——也就是说，遇到记忆问题先想一下：这是系统提取/巩固逻辑的锅（改 mission 重跑），还是外部世界真的变了、只有你知道（手动失效/编辑）。

## 编辑记忆

```python
await client.memory.update_memory(
    bank_id=BANK_ID,
    memory_id=memory_id,
    update_memory_request=UpdateMemoryRequest(
        text="The user visited Paris in 2023.",
        reason="wrong subject",
    ),
)
```

编辑之后会自动做三件事：**重新 embedding**、**删除这条记忆派生出的旧 Observation**、**重新巩固知识图**——但因果关系链条保持不变（不会因为编辑而把这条记忆从它原来的上下文里断开）。

## 失效记忆

```python
await client.memory.update_memory(
    bank_id=BANK_ID,
    memory_id=memory_id,
    update_memory_request=UpdateMemoryRequest(
        state="invalidated",
        reason="server decommissioned 2026-06-01",
    ),
)
```

失效之后这条记忆**从召回（recall）、巩固、知识图里全部消失**，但底层审计记录还在，随时可以恢复——`reason` 字段建议认真写，这是唯一留下"为什么失效"这个决策依据的地方。

## 一个容易忽略的点

"重新处理文档会重置管理历史"——如果是先手动编辑/失效过某些记忆，之后又因为系统性问题重新跑了一遍文档提取，**之前手动做的管理操作痕迹会被重置**。所以顺序上，系统性问题（改 mission 重新处理）要先于单条记忆的手动管理去做，不要反过来，不然手动调整的记录白费。

## 相关笔记

- [[homelab/AI Agent/Hermes + Hindsight 部署 SOP.md]] — 部署、冒烟测试
- [[homelab/AI Agent/Hindsight/Hindsight Bank Templates.md]] — bank 配置模板（`retain_mission`/`observations_mission` 这些字段在那篇有完整说明）
- [[homelab/AI Agent/Hindsight/Hindsight Memory Banks API.md]] — Bank 本身的概念，Memory 是 Bank 五个组成部分之一
