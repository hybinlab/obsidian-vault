---
publish: true
tags:
  - homelab
  - 事件记录
---
| 项目 | 内容 |
|---|---|
| 时间 | 2026-10-07 00:45~00:47、01:47~01:54；NtfyPublicDown 分别在 00:48、01:50 触发，各约 5 分钟后恢复 |
| 现象 | blackbox 探测 `https://ntfy.onecloud.xin/v1/health` 失败，触发 NtfyPublicDown |
| 影响 | 两段时间内所有经 frp 的公网服务不可用（ntfy、OpenList、calibre、openwebui、nexterm），手机收不到推送（恢复后补收） |
| 根因 | bastion 的 frpc 连不上 ECS 上的 frps，日志反复出现 `connect to server error: connection write timeout`、`session shutdown`，随后重连成功。**frps 端原因未确认**：时间正好是当晚在 ECS 上部署 ntfy、调整 nginx/frp 的时段，可能是 frps 重启，也可能是网络抖动 |
| 为什么当时没定位 | bastion 没有日志采集，事后才从 journal 里翻到 |
| 处理 | bastion 改用 Alloy，采集 frpc 的 journal 日志；新增 FrpcReconnecting 告警（10 分钟连接失败 >3 次） |
| 验证 | frpc 日志已进 Loki（`{job="frpc"}`），规则已加载 |
| 后续措施 | - [ ] ECS 上查 frps 2026-10-07 00:40~02:00 的日志，确认是重启还是网络问题 |

相关：[[Ansible 批量部署 Alloy 实战记录]]、[[Prometheus 告警 → ntfy 手机推送]]

**经验**：公网入口探测（blackbox）只能告诉你"不通"，要知道为什么不通，隧道两端的日志都得采集。
