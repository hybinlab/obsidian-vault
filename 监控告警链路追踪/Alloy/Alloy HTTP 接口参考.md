---
publish: true
---

Alloy 内置的 HTTP 服务器（就是 UI 那个 `127.0.0.1:12345`，配置见 [[监控告警链路追踪/Alloy/Alloy 顶层配置块参考.md]] 里的 `http` 块）除了给人看的 UI，还暴露了一批供程序调用的接口。

## 端点列表

| 端点 | 作用 | 返回 |
| --- | --- | --- |
| `/metrics` | Alloy 自身的运行指标，Prometheus 格式 | 指标文本 |
| `/-/ready` | 实例是不是已经完成初始配置加载 | 200 就绪 / 503 未就绪 |
| `/-/healthy` | 所有组件是不是都健康 | 200 健康 / 500 不健康 |
| `/-/reload` | 重新加载配置文件（热重载） | 200 成功 / 400 失败 |
| `/-/support` | 生成一份诊断信息打包，排障用 | 支持包（打包文件） |
| `/debug/pprof` | Go 语言标准的性能分析数据 | pprof 数据 |
| `/graphql`（实验性） | 用 GraphQL 查 Alloy 状态 | GraphQL 响应 |
| `/graphql/playground`（实验性，需手动开） | GraphQL 交互式查询界面 | 网页 |

## 用得上的几个

**`/metrics`**：把 Alloy 自己也当成一个采集目标，加进你的 `prometheus.scrape` 里，能监控"采集器本身"的健康度（比如丢了多少条日志、组件求值耗时）——这是 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里没细说的一层：Alloy 不仅采集别人的指标，自己也产出指标，同样可以被 Prometheus 抓。

**`/-/reload`**：[[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] 里讲过的热重载触发方式之一，`curl -X POST http://localhost:12345/-/reload`。

**`/-/ready` vs `/-/healthy`**：容易搞混但含义不一样——

- `/-/ready` 答的是"配置加载完了吗"，回答完就基本一直是 200，除非重新加载配置且还没跑完
- `/-/healthy` 答的是"所有组件现在都正常吗"，会随组件运行时状态实时变化（对应 [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] 里的四种健康状态）

**官方明确提示**：`/-/healthy` **不适合当 Kubernetes 的存活探针（liveness probe）**——单个组件不健康（比如某个 exporter 临时连不上）不代表整个 Alloy 进程需要被杀掉重启，用它做 liveness 会导致进程被无谓地反复重启。真要做健康检查，`/-/ready` 更适合当 liveness，`/-/healthy` 更适合当 readiness 或者单纯拿来监控告警用。

**`/-/support`**：一键收集诊断信息打包，遇到解决不了的问题找社区/官方求助前先跑一下这个，比截图配置文件描述现象更有效。

## 小结

日常用得上的就三个：`/metrics`（纳入监控）、`/-/reload`（热重载）、`/-/ready`（健康探针，注意不是 `/-/healthy`）。pprof 和 GraphQL 是排查性能问题/深度查询状态时才会碰的高级功能。

## 相关笔记

- [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] — 健康状态、热重载机制
- [[监控告警链路追踪/Alloy/Alloy 顶层配置块参考.md]] — `http` 块怎么配监听地址/TLS
