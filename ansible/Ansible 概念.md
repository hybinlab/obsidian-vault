---
publish: true
---

## 核心术语

| 术语            | 中文   | 含义                                         |
| ------------- | ---- | ------------------------------------------ |
| Control node  | 控制节点 | 运行 Ansible CLI 工具的计算机，可以是任何满足 Ansible 软件要求的机器    |
| Managed nodes | 受管节点 | Ansible 要管理的目标设备或服务器，被控制节点通过 SSH 进行管理          |
| Inventory     | 清单   | 受管节点的列表，可以指定每个节点的 IP 地址、主机名、特定信息等          |
| Playbook      | 剧本   | 包含执行任务的 YAML 文件，是一系列 Play 的集合                  |
| Play          | 剧     | 执行的基本单位，将受管节点映射到任务，剧本中包含一个或多个 Play       |
| Task          | 任务   | 受管节点上要执行的操作定义，是 Play 中最小的可执行单位              |
| Handler       | 处理程序 | 特殊的任务，仅在前一任务通知且状态为"已更改"时才执行              |
| Module        | 模块   | Ansible 复制并在受管节点上执行的代码或二进制文件，默认包含上千款       |
| Role          | 角色   | 可重用内容的分发格式，包含任务、处理程序、变量、插件、模板和文件        |
| Plugin        | 插件   | 扩展 Ansible 功能的代码片段                           |
| Collection    | 集合   | Ansible 内容的分发格式，可包含剧本、角色、模块和插件               |

## 核心概念

- Ansible 基于 **SSH 协议**，无需客户端程序，只要知道受管主机的账号密码就能直接远程控制
- 通过调用**模块**实现具体功能，几乎可以满足一切需求；管理模式也非常丰富（命令行 / Playbook 等）
- 如需更高级功能，可以用 **Python** 对其进行二次开发
- 已被 AWS、GCP、Azure、Cisco、HP、VMware、Twitter 等广泛采纳
- 从 2020 年 8 月起，RHCE 考试内容改为配置多款服务 → Ansible 专项考核

## 安装注意事项

### 系统要求

- Ansible 默认**不在 RHEL 8 系统的镜像仓库**中
- 需要从 **"Extra Packages for Enterprise Linux" (EPEL)** 扩展软件包仓库获取
- EPEL 由红帽公司提供，用于创建、维护和管理企业版 Linux 的高质量扩展包
- 通用于 RHEL、CentOS、Oracle Linux 等多种红帽系企业版系统

### 安装后验证

```bash
ansible --version
# 确认版本、配置文件路径、模块搜索路径等
```

## 主机清单（Inventory）配置

详见 [[ansible/Ansible Inventory.md]]

## 配置文件

详见 [[ansible/Ansible 配置.md]]

## 模块与命令

- [[ansible/Ansible 模块.md]] — 常用模块和查询方法
- [[ansible/Ansible Doc.md]] — ansible-doc 工具，查看模块和插件文档
- [[ansible/Ansible CLI.md]] — 临时命令参数、检查模式、测试连通性
- [[ansible/Ansible Console.md]] — 交互式命令行工具，快速执行多个临时命令
- [[ansible/Playbook/Ansible Playbook 编写.md]] — Playbook 的 YAML 语法、Play/Task 结构、FQCN、幂等性
- [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] — 变量、条件、循环、Handler 等14个进阶主题一览（按需展开）
- [[ansible/Playbook/Ansible Playbook.md]] — ansible-playbook 执行，标签、检查模式、权限提升等
- [[ansible/Ansible Pull.md]] — 拉取式架构，受管节点主动拉取执行（大规模/去中心化）
- [[ansible/Ansible Galaxy.md]] — 管理角色和集合，从 Galaxy 市场安装可复用组件
- [[ansible/Ansible Vault.md]] — 加密敏感数据（密码、密钥），按需学习，见下方判断

## 要不要用 Vault？

Vault 用于加密要提交到 Git 的敏感数据，实际是否需要看场景：

- **需要**：playbook 要提交到共享/公开仓库，且含密码、API 密钥等敏感信息；团队协作、多人共享仓库
- **可以不用**：个人 homelab、不打算把仓库公开或共享 —— 直接 `.gitignore` 排除含密码的变量文件更省事
- **企业环境常见替代**：CI/CD 平台自带 Secret 注入（GitHub Actions/GitLab CI）、AWX/AAP 的 Credential 管理，比 Vault 更适合团队规模化协作

详见 [[ansible/Ansible Vault.md]]

## 实战练习

看完笔记不代表会用，练手清单见 [[ansible/Ansible 实战练习清单.md]]
