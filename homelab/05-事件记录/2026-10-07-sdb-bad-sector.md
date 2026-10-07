---
publish: true
tags:
  - homelab
  - 事件记录
---
| 项目 | 内容 |
|---|---|
| 时间 | 2026-10-05 15:30、2026-10-07 15:32 两次报错 → 2026-10-07 约 18:50 发现 |
| 现象 | docker-host 内核日志：`I/O error, dev sdb, sector 1471431 op 0x0:(READ)`、`Sense Key : Aborted Command`，每次连续重试 3 次 |
| 影响 | 暂无可见影响。sdb 是 `/mnt/jellyfin`（Jellyfin 媒体库约 431G） |
| 根因 | **疑似坏道**（未最终确认）：两次都是读**同一个扇区**失败。sdb 是直通给 docker-host 的 WD WD10JPVX（1TB 2.5 寸 5400 转笔记本盘），时间点接近（都在下午 15:30 左右），可能是某个定时任务（如媒体库扫描）读到了这个扇区 |
| 为什么之前没发现 | 日志采集了，但没有任何日志告警 |
| 处理 | 上线 Loki 日志告警，新增 DiskIOError（syslog 出现磁盘 I/O 错误即推送） |
| 验证 | 规则已加载；用测试标记验证过 Loki ruler → Alertmanager → ntfy 整条链路 |
| 后续措施 | - [ ] 在 PVE 上 `smartctl -a /dev/sdb`，看 Reallocated_Sector_Ct、Current_Pending_Sector、Offline_Uncorrectable<br>- [ ] 如果确认坏道在增长，考虑把媒体迁移到别的盘（目前没有第二份） |

相关：[[Jellyfin]]、[[04-备份与恢复]]、[[Loki 日志告警与监控组件自监控]]

**经验**：日志只采集不告警等于没采集。这条是日志告警刚配好、查基线时顺手发现的。
