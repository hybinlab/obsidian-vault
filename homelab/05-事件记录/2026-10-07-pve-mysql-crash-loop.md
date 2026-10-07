---
publish: true
tags:
  - homelab
  - 事件记录
---
| 项目 | 内容 |
|---|---|
| 时间 | 2026-10-02 22:50 开始 → 2026-10-07 19:06 发现 → 当晚处理完毕（约 5 天） |
| 现象 | 手机收到 `AlloyDroppingLogs @ docker-host`，10 分钟丢弃 1.5 万~2.6 万条日志，丢弃的全是几天前的旧时间戳 |
| 影响 | 用户无感知：pveui 实际连的是 database 上的外部 MySQL，`pve-mysql` 是多余的。但它崩溃重启了 **6937 次**，日志被 Alloy 反复重读、累计丢弃约 25 万条 |
| 根因 | pveui 有两个 compose 文件。10-02 先用默认的一体化 `docker-compose.yml` 启动了一次（带 MySQL），`.env` 里没填 `MYSQL_ROOT_PASSWORD`，MySQL 首次初始化即退出，`restart: always` 每分钟重启；1 分钟后改用 `docker-compose.dev.yml` 启动了前后端，`pve-mysql` 被遗留。<br>丢日志的原因：`loki.source.docker` 在容器每次重启后从头重读日志，旧条目超出 Loki 接收窗口被拒（`entry too far behind`） |
| 为什么 5 天没发现 | 没有容器级监控；cAdvisor 的 `container_start_time_seconds` 也识别不了同一容器的重启 |
| 处理 | 停止并关闭自动重启 → 查明是遗留容器后删除容器和空卷 `pveui_mysql-data`（`pveui_media-data` 保留） |
| 验证 | Alloy 丢弃计数不再增长；pveui 前后端正常 |
| 后续措施 | - [x] 部署 cAdvisor + Docker `RestartCount` 采集，新增 ContainerRestartLoop 告警（15 分钟重启 ≥3 次） ✅ 2026-10-07<br>- [x] [[pveui]] 运维手册写明只能用 `docker-compose.dev.yml` 启动 ✅ 2026-10-07<br>- [ ] 考虑在 pveui 仓库里把 dev 版本改名或在 README 注明 |

详细过程：[[容器监控与告警（cAdvisor + Docker 重启次数）]]

**经验**：`AlloyDroppingLogs` 突然出现、丢的全是旧时间戳 → 先查有没有容器在崩溃循环。
