## 定位

Ansible（[[ansible/Ansible 概念.md]]）只是 SRE 工具链里的一小块——**配置管理**。掌握 playbook + role + inventory 就够了，不用深挖到写自定义 module/plugin（对应 [[ansible/Ansible 概念.md]] 里"要不要用 Plugin 开发指南"的判断，结论是不用）。

SRE 要求的面宽得多，这篇笔记是整体地图，未来各领域的笔记都挂在这个文件夹下。

## 技能地图

| 领域           | 核心工具/概念                                                                                  | 现状                                                                         |
| ------------ | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **配置管理**     | Ansible：playbook、role、inventory                                                          | 已系统学习，见 [[ansible/Ansible 概念.md]]                                          |
| **基础设施即代码**  | Terraform 建资源（VM、网络、存储），Ansible 装软件配置；前提是懂云网络基础（VPC/子网/安全组/负载均衡/DNS解析）                   | 未开始                                                                        |
| **容器与编排**    | Docker（已会）→ Kubernetes（部署、调度、网络、存储）                                                      | Docker 已会，K8s 未开始，SRE 岗位默认门槛                                               |
| **CI/CD**    | Jenkins / GitLab CI / GitHub Actions，至少熟一个，代码提交到生产部署全流程自动化                               | 未开始                                                                        |
| **监控告警**     | Prometheus + Grafana（标配），日志（ELK/Loki），链路追踪（Jaeger）                                       | 阿里云有监控搭建经验，需系统化，笔记见 [[监控告警链路追踪]]                                             |
| **数据库运维**    | MySQL/PostgreSQL/Redis 其中一两个：主从复制、备份恢复、连接池与调优、常见故障排查                                     | 未开始                                                                        |
| **密钥/证书管理**  | Vault 或云厂商密钥服务，TLS 证书签发与轮换，敏感配置不落明文                                                      | 未开始                                                                        |
| **Linux 深度** | 网络（iptables/nftables、DNS、负载均衡）、性能排查（CPU/内存/IO/网络瓶颈）、存储、systemd                           | 网络排障已有 [[linux/网络排障/网络故障排查 Runbook.md]]，防火墙见 [[linux/防火墙/防火墙总览.md]]，性能排查待补 |
| **编程/脚本**    | Python 或 Go，写工具/operator/自动化修复脚本；Shell 只是入门                                              | 待评估现状                                                                      |
| **SRE 理念**   | SLI/SLO/SLA、error budget、toil 消减、事故复盘（postmortem），容量规划、高可用设计（备份/多副本/故障转移），Google SRE 那本书 | 未开始                                                                        |

## 关于 Ansible 的取舍原则（可复用到其他工具）

Ansible 笔记建设过程中形成的判断标准，值得套用到后续 Terraform/K8s 等工具的学习上：

- **按需展开，不追求覆盖官方文档全部内容**：进阶主题先建索引，实际卡在哪个概念再展开成正式笔记（参考 [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]]）
- **区分"用得上"和"知识存档"**：像 Vault、Pull 这类当前场景用不上但可能以后有用的内容，写清楚判断依据存档，不必深究细节
- **拒绝纯知识堆砌，工具书价值有限**：真正值钱的是判断逻辑和决策路径（参考 [[linux/网络排障/网络故障排查 Runbook.md]] 的 Runbook 思路），命令细节随时能查
- **练习要落到真实场景，不做纯 Demo**：练习清单的终局是产出能在 homelab 里长期复用的成果（参考 [[ansible/Ansible 实战练习清单.md]] 第九关的 docker-host.yml）

## 路线图

![[SRE/SRE 学习路线图.png]]

## 学习顺序建议

不追求同时铺开，按 ROI 排：

1. **K8s** — SRE 岗位硬门槛，且 Docker 基础已经有了，衔接成本低；开始前先花小半天过一遍云网络基础概念（子网、路由、DNS解析、负载均衡原理），否则 K8s 的 CNI/Service/Ingress 会学得很吃力
2. **监控体系系统化** — 已有阿里云经验，补齐 Prometheus/Grafana + 日志/链路追踪的完整链路
3. **Terraform** — 和 Ansible 配合形成完整 IaC 闭环（Terraform 建机器，Ansible 装软件）
4. **CI/CD** — 前三项打底后，把整个流程串起来
5. **编程语言深化 + SRE 理念** — 贯穿始终，不是单独一个阶段

## 相关笔记索引

- [[ansible/Ansible 概念.md]] — 配置管理，已完成体系化整理
- [[linux/网络排障/网络故障排查 Runbook.md]] — Linux 网络排障
- [[linux/防火墙/防火墙总览.md]] — 防火墙工具对比
