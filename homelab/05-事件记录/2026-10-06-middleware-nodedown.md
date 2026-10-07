---
publish: true
tags:
  - homelab
  - 事件记录
---
| 项目 | 内容 |
|---|---|
| 时间 | 2026-10-06 22:43 告警 → 2026-10-07 01:58 恢复（停止抓取）→ 当晚查明真因并接入监控 |
| 现象 | NodeDown @ middleware：192.168.31.6 能 ping 通，9100 端口拒绝连接 |
| 影响 | middleware（Redis）没有任何监控；告警链路刚打通，这条一直在响 |
| 根因 | **监控配置和实际不符**：Prometheus 里一直配着 `192.168.31.6:9100`，但 middleware 上**从来没装过 node_exporter**。一开始误判为"node_exporter 停了"，后来通过 Ansible 上机检查才查明 |
| 处理 | 先注释掉抓取目标止住告警；之后用 Ansible 给 middleware 装 Alloy（指标 remote write + 日志），并加入 RemoteWriteStale、LogIngestionStopped 规则 |
| 验证 | `up{job="node",instance="middleware"}` 为 1，日志进 Loki |
| 后续措施 | - [x] 主机清单改为自动生成，"监控"列实时查询，配置与实际不符会直接显示 ✅ 2026-10-07 |

相关：[[Ansible 批量部署 Alloy 实战记录]]、[[01-主机清单]]

**经验**：看到 down 不要先假设"服务停了"，先上机确认装没装。
