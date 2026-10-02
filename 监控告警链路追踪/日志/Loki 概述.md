---
publish: true
tags:
  - Loki
cssclasses:
  - Loki
---

## 定位

Grafana Loki 是受 Prometheus 启发的**日志聚合系统**，特点是水平扩展、高可用、多租户。与 Prometheus 拉取指标不同，Loki 采用**推送**方式收集日志（由 [[Grafana Alloy 概述|Alloy]] 等采集器推送）。

来源：https://grafana.com/docs/loki/latest/get-started/overview/

## 解决的问题

传统日志系统（如 ELK）对日志**全文建索引**，索引体积大，存储和运维成本高。

Loki 的做法：**只索引元数据（标签），不索引日志内容**。日志本身压缩成块，存放在 S3、GCS 等对象存储中。

## 为什么选择它

| 维度 | 说明 |
|---|---|
| 成本低 | 索引小，日志块放对象存储 |
| 扩展性 | 从树莓派到每天 PB 级；可单二进制、HA monolithic 或微服务部署 |
| 多租户 | 多个租户共享一个实例，数据和请求完全隔离 |
| 查询语言 | LogQL 类似 PromQL，Prometheus 用户上手快，还能从日志生成指标 |
| 生态集成 | 与 Grafana、Mimir、Tempo 集成，日志、指标、追踪统一在一个平台 |
| 告警 | 内置 ruler 持续评估日志查询，可对接 Alertmanager |

## 笔记索引

### 入门与部署

- [[Loki 快速上手教程]]：用 Docker Compose 跑通 Alloy → Loki → Grafana，含配置逐块解读
- [[Loki 配置最佳实践]]：时间顺序、压缩、chunk、limits、ingester 推荐配置，含实测生效值
- [[Loki 标签最佳实践]]：静态与动态标签、基数、高基数标签排查

### LogQL 查询语言

建议按顺序阅读：

1. [[LogQL 概述]]：查询结构与两类查询
2. [[LogQL 日志查询]]：流选择器、行过滤、解析器、标签过滤、格式化
3. [[LogQL 指标查询]]：范围聚合、`unwrap`、聚合运算符，写 Grafana 面板用
4. [[LogQL 模板函数]]：`line_format` / `label_format` 中的函数，以示例为主
5. [[LogQL 查询示例]]：官方示例汇总，按场景查
6. [[LogQL 查询最佳实践]]：写出高效查询的顺序与反例

### 采集端（Alloy）

- [[Grafana Alloy 概述]]：Alloy 的定位
- [[Alloy Loki 组件总览]]：`loki.*` 组件
- [[Alloy 采集日志发送到 Loki]]：采集并写入 Loki
- [[Alloy 处理日志（多阶段 Pipeline）]]：日志处理流水线
- [[Alloy 采集 Loki 日志实战记录]]：自建环境的实战记录
