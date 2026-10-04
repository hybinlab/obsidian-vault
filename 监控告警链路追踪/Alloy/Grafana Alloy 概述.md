---
publish: true
---

## 定位

Grafana Alloy 是一个开源**遥测数据采集器**（collector），本质是内嵌了完整 OpenTelemetry Collector 的一个发行版。它不是存储或展示层，而是"采集层"，作用是把 metrics、logs、traces、profiles 这四类信号统一采集、处理，再转发给后端（Prometheus/Grafana Cloud、Loki、Tempo、Pyroscope 等）。

在整个可观测性链路里的位置：数据源 → **Alloy（采集/处理/转发）** → 存储后端（Prometheus/Loki/Tempo）→ Grafana 展示。

## 解决的痛点（why-alloy）

传统做法要给不同信号分别部署工具：Prometheus（指标）、Promtail/Fluentd（日志）、Jaeger agent（链路追踪）——每个工具配置语法、部署模型、运维方式都不一样，维护成本高。

Alloy 的思路是"学一个工具、部署一个收集器、维护一套系统"：

- **单一部署覆盖四种信号**，不用多套agent
- **同时兼容 Prometheus 和 OpenTelemetry 两套生态**，不用二选一
- 配置语言支持条件逻辑、跨组件引用数据、可复用模块，比单纯的"采集转发"更灵活
- 供应商中立，可以同时发给 Grafana Cloud、自建后端或多个目标

官方也坦诚：如果只是采集基础 Prometheus 指标，用 Prometheus Agent 可能更简单；如果已经深度绑定某个特定收集器生态，未必需要换成 Alloy。

## 工作原理（how-alloy-works）

核心概念是 **Component（组件）** 和 **Pipeline（管道）**：

- 每个组件只做一件事：比如从 Prometheus endpoint 抓取指标、接收 OTel 数据、做过滤/脱敏/转换、发送到某个后端
- 把多个组件用配置文件连起来就是一条 pipeline，数据在组件间流动
- 配置语言是**表达式式**的，可以在一个组件里引用另一个组件的数据，动态组装管道

Alloy 在整条链路上做三件事：**采集**（scrape/receiver/日志 tail/服务发现）→ **处理**（过滤、脱敏、打标签、转换）→ **投递**（发到任意兼容后端）。

自带一个内置 Web UI，可以可视化查看 pipeline 结构、组件状态，方便调试。

## 和 OpenTelemetry Collector 的关系（otel_alloy）

不是"基于"OTel Collector 重写，而是把 OTel Collector 作为一个独立引擎**嵌入**进 Alloy 可执行文件里，同一个二进制里有两套引擎可选：

| 维度 | Alloy 默认引擎 | 内嵌的 OTel 引擎 |
| --- | --- | --- |
| 配置语法 | Alloy 专有语法 | 标准 OpenTelemetry YAML |
| 成熟度 | 稳定、向后兼容 | 实验性 |
| 优化方向 | Prometheus 拉式采集 | OTLP 推式、OTel 原生生态 |
| 特色能力 | 集群、内置 UI、调试工具 | 兼容标准 Collector 生态组件 |

选 Alloy 而不是原生 OTel Collector 的理由：已有的 OTel Collector YAML 配置可以直接套用（无需转写成 Alloy 语法）、一个二进制搞定多种工作负载、默认引擎还带了 Prometheus/K8s 监控等 Grafana 专属增强能力。两个引擎也可以按需切换甚至并行跑。

## 系统要求（requirements）

- **支持平台**：Linux、Windows、macOS、FreeBSD（对应架构 AMD64/ARM64，具体以 Supported platforms 页面为准）
- **硬件**：文档未给硬性最低配置，视部署模式（边缘采集 / 网关聚合 / 混合）资源消耗差异较大，需要参考官方"资源使用估算"指南按实际负载评估
- **网络**：默认内置 HTTP 服务（含 UI）监听 `127.0.0.1:12345`；需要出站网络连接把数据发到后端

## 部署方式回顾

Docker/Podman 容器、Kubernetes(Helm)/OpenShift、Linux 包管理器(deb/rpm)、独立二进制、或用 Ansible/Chef/Puppet 装成系统服务，任选其一，同一台机器不需要重复部署。判断标准是采集对象：容器化服务用容器部署更省事；要采集宿主机本身（journal/文件系统日志等）用系统服务更方便处理权限和路径。

## 当前场景的取舍判断（指标 vs 日志要分开看）

**指标采集**：homelab 规模是"中心 Prometheus 直接够得着所有目标"，Prometheus 自带 scrape 引擎，装 Alloy 纯属多此一举——这条结论成立，见后面的"实测反例"。

**日志采集**：这条不适用。**Prometheus 本身不采集日志**，它只做指标，从来没有"Prometheus 自带 scrape 日志"这个选项可比较——要把日志送进 Loki，天生就需要一个独立 agent（Promtail 或 Alloy 二选一）。所以 homelab 现在用 Alloy 采日志（[[Alloy 采集日志发送到 Loki]]）不是"为了用新技术而用"，是日志采集这个环节本来就绕不开一个采集端 agent，选 Alloy 而不是 Promtail 只是因为 Grafana 官方已经把 Promtail 标为 deprecated、推荐迁移到 Alloy。

也就是说：**指标场景下 Alloy 是多余的替代品，日志场景下 Alloy 是必需的采集端**——这是两个独立的判断，不要混着套用同一个"要不要用 Alloy"的结论。链路追踪同理，Prometheus/Loki 都不采 trace，一旦以后要接 Jaeger/Tempo，同样需要一个采集端，Alloy 也是候选之一。

**实测反例**：homelab 想把一台阿里云 ECS 纳入监控，场景是"homelab 无公网 IP、ECS 有公网 IP"。看着像是"网络拓扑限制"的触发条件，实际算下来最简方案是 Prometheus 直接主动拉 ECS 的公网 IP（出方向天然可达，不需要任何隧道），三步搞定，比部署 Alloy + frp 隧道推送简单得多。结论：单节点场景下，即使网络不对称，只要有一个方向能直接连通，就该走最简单的那个方向，不要为了"看起来更规范"上 Alloy。真正需要 Alloy push 模式的前提是**双向都不通**（比如中心也没公网 IP、彼此都在各自的 NAT 后面，谁都连不到谁，才需要靠 frp/Alloy 这类中转+推送方案）。

## 相关笔记

- [[SRE/SRE 学习路径.md]] — 监控告警属于系统化学习的第二优先级
- [[监控告警链路追踪/Alloy/Alloy 配置语法入门.md]] — Block/Attribute/Component/Expression 配置语言细节
- [[监控告警链路追踪/Alloy/Alloy 组件配置规则.md]] — 必填/可选参数、依赖图、循环引用防护
- [[监控告警链路追踪/Alloy/Alloy 数据类型.md]] — number/string/array/object/Secret/Capsule
- [[监控告警链路追踪/Alloy/Alloy 运算符.md]] — 算术/比较/逻辑/访问运算符
- [[监控告警链路追踪/Alloy/Alloy 函数调用.md]] — 标准库函数、组件导出函数
- [[监控告警链路追踪/Alloy/Alloy 构建 Pipeline.md]] — 线性/多阶段/扇出/链式过滤等管道模式
- [[监控告警链路追踪/Alloy/Alloy 组件控制器与生命周期.md]] — 健康状态、热重载、优雅降级
- [[监控告警链路追踪/Alloy/Alloy 自定义组件.md]] — declare/argument/export、Module 跨文件复用
- [[监控告警链路追踪/Alloy/Alloy 采集 Prometheus 指标.md]] — discovery/scrape/remote_write 实战配方
- [[Alloy 采集日志发送到 Loki]] — 日志管道实战，当前 homelab 实际在用
- [[Alloy 处理日志（多阶段 Pipeline）]] — stage.json/timestamp/drop/labels/output 逐步拆解
- [[监控告警链路追踪/Alloy/Alloy 顶层配置块参考.md]] — logging/http/livedebugging/remotecfg/import.*/foreach
- [[监控告警链路追踪/日志/Alloy Loki 组件总览.md]] — 23 个 loki.* 组件索引
- [[监控告警链路追踪/Alloy/Alloy HTTP 接口参考.md]] — /metrics /-/reload /-/ready /-/healthy 等端点
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Docker.md]] — homelab 实际在用
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Linux.md]] — apt/dnf/zypper 包管理器 + systemd
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Ansible.md]] — 多机批量部署才划算
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - macOS.md]] — 本地调试用
