---
publish: true
tags:
  - homelab
  - 事件记录
  - hindsight
  - 性能
---
| 项目 | 内容 |
|---|---|
| 时间 | 2026-10-02 起持续复发 → 2026-10-28 定位 → 2026-11-01 修复 |
| 现象 | agent VM（101）CPU 100% 持续数十分钟至数小时；Hindsight API 的 recall 请求超时/被取消；日志刷 `Reflect operation timed out after 300 seconds`；单日日志量 1.1MB（平时 27–50KB） |
| 影响 | **Hindsight 记忆功能整体不可用**——recall 无响应，agent 读不到长期记忆；agent VM 上还跑着 Hermes 与 Ansible 控制节点，满载期间整机响应劣化 |
| 根因 | **默认配置与硬件规格不匹配**：agent VM 仅 2C/6G，纯 CPU 跑 bge-m3 嵌入 + bge-reranker-base 交叉编码器重排。`reranker_max_candidates` 默认 300，实测单次重排 215s；而 `reflect_wall_timeout` 默认 300s —— **一次工具调用就吃掉 2/3 预算**，`reflect_max_iterations=10` 在此单次耗时下根本跑不完，必然撞墙 |
| 放大链路 | reflect 撞墙 → `TimeoutError` → 任务重试 ×3 → 每次重试再跑一遍满 CPU 的重排 → 自旋。两个 mental model 并发刷新，各开 4 个 executor worker × torch 2 线程 = 16 线程槽挤 2 核 |
| 触发源 | `refresh_after_consolidation: true` —— 每轮对话产生事实 → consolidation → 自动刷新 mental model → 必超时。10-02 起两个 mental model 的 `last_refreshed_at` 再未更新，**一个月零成功** |
| 处理 | 三步，变量分离以便验证：<br>① env：`RERANKER_MAX_CANDIDATES` 300→**50**，`REFLECT_WALL_TIMEOUT` 300→**900**（备份 `hindsight.env.bak.20261101`）<br>② 硬件：PVE 上 101 agent 由 2C/6G 升 **4C/8G**（103 database 内存 2G→4G，CPU 降 2C）<br>③ 止血：bank config `PATCH mental_model_min_refresh_interval_seconds=86400`（per-bank，无需重启） |
| 验证 | reflect 耗时 233–264s 稳定成功（原为必超时）；重排 48s/次（原 215s）；超时 0 次；两个 mental model 的 `last_refreshed_at` 更新到 2026-11-01，为一个月来首次成功；24h 间隔生效的日志证据：`Task ... deferred until 2026-11-02 15:55:44: min_refresh_interval_seconds=86400` |
| 后续措施 | - [x] env 降重排候选数 + 抬墙钟预算 ✅ 2026-11-01<br>- [x] agent VM 升 4C/8G ✅ 2026-11-01<br>- [x] mental model 刷新加 24h 最小间隔 ✅ 2026-11-01<br>- [ ] 写一份 homelab 现状的权威输入文档，让 mental model 的 source_query 指向它，而不是每次从记忆库碎片重新拼图（reflect 可更快更准）<br>- [ ] 观察 2026-11-02 15:55 那次真跑的 reflect 耗时，确认稳定在 300s 内；若仍超时则瓶颈在 LLM 侧而非 CPU |

相关：[[Hermes + Hindsight（Bare Metal）部署 SOP]]、[[00-现状总览]]、[[01-主机清单]]

**经验**：

- **默认配置不是安全配置。**Hindsight 的默认 `reranker_max_candidates=300` 隐含假设"机器有 GPU 或很多核"。在 2 核纯 CPU 上,这个默认值会稳定地把 agent 打死。**任何默认性能参数都要对照自己的硬件规格重新评估。**
- **估算基准必须用真实数据长度。**首次基准用几十字短句测出"50 候选 21s",实际生产中 fact 普遍约 200 字,实测 53s —— **偏差 2.5 倍**。交叉编码器是逐对计算,耗时随文档长度近似线性增长。
- **超时重试会把单点故障变成持续故障。**一次超时不可怕,可怕的是每次重试都重跑满 CPU 的那一段,让故障从"一次事件"变成"永久自旋"。查因时先看**重试次数**和**单次成本**,不只是看有没有报错。
- **CPU 满载 + 上游服务无响应 = 先看上游自己的资源,别只查上游的依赖。**本次的第一直觉是"数据库慢",实际是本机推理把 API 线程饿死了。
- **止血点和根治要分开做。**加最小刷新间隔(止血)与提规格(根治)分开落地,才有干净的对比数据。顺序反了,两个变量混在一起,无法归因。
- **per-bank 配置 API 能改的东西,就别改全局 env。**`min_refresh_interval_seconds` 走 bank config,无需重启、不影响其他 bank;`reranker_max_candidates` 是全局静态参数,才需要改 env + 重启。
