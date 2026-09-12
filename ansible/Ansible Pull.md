---
publish: true
---
## ansible-pull 拉取式架构

`ansible-pull` 将 Ansible 的默认**推送架构**（Push：控制节点推送任务到受管节点）转变为**拉取架构**（Pull：受管节点主动拉取 Playbook 并执行），实现更高的可扩展性和去中心化管理。

## 推送 vs 拉取

| 特点 | Push（ansible-playbook） | Pull（ansible-pull） |
|------|--------------------------|----------------------|
| 执行方向 | 控制节点 → 受管节点 | 受管节点 ← 版本控制系统 |
| 架构 | 中央集中式 | 去中心化 |
| 可扩展性 | 受控于中央控制节点性能 | 高度可扩展（无中央瓶颈） |
| 场景 | 少量主机、实时管理 | 大规模部署、定时补救 |
| 依赖 | SSH 连接正常 | Git/SVN 仓库可访问 |
| 网络要求 | 控制节点能访问所有节点 | 节点能访问代码仓库 |

## 工作原理

1. **在受管节点安装 Ansible**：通过引导脚本或包管理器安装
2. **从 Git 仓库克隆 Playbook**：`git clone <repo_url>`
3. **执行本地 Playbook**：`ansible-playbook local.yml`（节点本地执行）
4. **定时重复**：通过 cron 定时运行上述流程

```
Git Repository
      ↑
      | git pull
      |
  Managed Node (ansible-pull via cron)
      |
      ├─ clone/update from git
      └─ execute playbook locally
```

## 基本用法

### 一次性执行

```bash
# 从 Git 仓库拉取并执行 playbook
ansible-pull -U https://github.com/user/ansible-repo.git

# 指定分支
ansible-pull -U https://github.com/user/ansible-repo.git -C develop

# 指定 playbook 文件（默认查找 local.yml）
ansible-pull -U https://github.com/user/ansible-repo.git site.yml

# 指定本地仓库目录
ansible-pull -U https://github.com/user/ansible-repo.git -d /opt/ansible
```

### 定时执行（cron）

```bash
# 添加 cron 任务：每小时执行一次
ansible-pull -U https://github.com/user/ansible-repo.git \
  -C master \
  -d /opt/ansible \
  -s 60

# crontab 条目示例
0 * * * * /usr/bin/ansible-pull -U https://github.com/user/ansible-repo.git \
  -C master \
  -d /opt/ansible \
  -s 60
```

## 常用参数

### 仓库相关

|参数|功能|
|---|---|
|-U / --url|**必需**：指定 Git/SVN/Hg 仓库 URL|
|-C / --checkout|指定分支、标签或提交 hash（默认 master）|
|-d / --directory|仓库在本地的检出路径（默认 ~/ansible-pull）|
|-m / --module-name|VCS 模块类型：git、svn、hg（默认 git）|

### 执行控制

|参数|功能|
|---|---|
|-s / --sleep|随机延迟秒数（0-N），避免大规模节点同时请求 Git|
|-o / --only-if-changed|仅在仓库有更新时执行 playbook|
|-f / --force|即使 Git 更新失败也强制执行|
|-i / --inventory|指定清单文件（通常无需，node 为自己）|

### Playbook 执行选项

|参数|功能|
|---|---|
|-t / --tags|仅执行特定标签的任务|
|--skip-tags|跳过特定标签的任务|
|-b / --become|以提权方式执行|
|-K / --ask-become-pass|提示输入提权密码|
|-u / --user|指定远程用户|
|-e / --extra-vars|传递额外变量|
|-v / --verbose|调试输出|
|-C / --check|检查模式|
|--syntax-check|检查语法|

## 高级用法

### 自动主机名映射

`ansible-pull` 会自动寻找与当前主机对应的 playbook：

```bash
# 假设仓库结构如下：
# repo/
# ├── local.yml           # 默认，所有主机执行
# ├── webserver.yml       # hostname=webserver 时执行
# └── db.yml              # hostname=db 时执行

# node1 上执行，会依次查找并执行：
# 1. db.example.com.yml（FQDN）
# 2. db.yml（hostname）
# 3. local.yml（最后的备选）
```

### 仓库结构示例

```
ansible-repo/
├── local.yml                    # 通用配置（所有节点）
├── webserver.yml               # Web 服务器专用
├── db.yml                       # 数据库服务器专用
├── group_vars/
│   ├── webservers.yml
│   └── databases.yml
├── host_vars/
│   ├── web1.example.com.yml
│   └── db1.example.com.yml
├── roles/
│   ├── web/
│   ├── database/
│   └── common/
└── README.md
```

### 日志收集

```yaml
# local.yml - 结合 fetch 模块收集日志
---
- hosts: localhost
  gather_facts: yes
  tasks:
    - name: Common config
      include_role:
        name: common

    - name: Deploy role（可能失败）
      include_role:
        name: "{{ ansible_hostname.split('.')[0] }}"
      ignore_errors: yes

    - name: Fetch execution log back to central repo
      fetch:
        src: /var/log/ansible-pull.log
        dest: logs/{{ inventory_hostname }}/
        flat: yes
```

## 实战例子

### 例子1：基础拉取式部署

```bash
# 在每个要被管理的节点上运行一次（可通过 cloud-init 自动化）
ansible-pull -U https://github.com/mycompany/ansible.git \
  -C main \
  -d /opt/ansible \
  -o

# 然后配置 cron 定时执行
cat > /etc/cron.d/ansible-pull << 'EOF'
# 每30分钟执行一次，随机延迟0-60秒
*/30 * * * * root /usr/bin/ansible-pull \
  -U https://github.com/mycompany/ansible.git \
  -C main \
  -d /opt/ansible \
  -s 60 \
  -o >> /var/log/ansible-pull.log 2>&1
EOF
```

### 例子2：多分支管理（环境隔离）

```bash
# 开发环境节点
ansible-pull -U https://github.com/mycompany/ansible.git \
  -C develop \
  -d /opt/ansible

# 生产环境节点
ansible-pull -U https://github.com/mycompany/ansible.git \
  -C main \
  -d /opt/ansible

# 灾难恢复环境
ansible-pull -U https://github.com/mycompany/ansible.git \
  -C hotfix \
  -d /opt/ansible
```

### 例子3：Cloud-Init 集成（自动化初始化）

```yaml
# AWS EC2 / 其他云平台 cloud-init script
#cloud-config
runcmd:
  - yum install -y ansible git
  - ansible-pull \
      -U https://github.com/mycompany/ansible.git \
      -C main \
      -d /opt/ansible
  
  # 配置 cron
  - echo '*/30 * * * * root /usr/bin/ansible-pull -U https://github.com/mycompany/ansible.git -C main -d /opt/ansible -s 60 -o' | crontab -
```

### 例子4：带认证的私有仓库

```bash
# 使用 SSH 密钥（需提前配置 SSH 密钥对）
ansible-pull -U git@github.com:mycompany/ansible.git \
  -C main \
  -d /opt/ansible

# 使用 HTTPS + Token（GitHub）
ansible-pull -U https://token:x-oauth-basic@github.com/mycompany/ansible.git \
  -C main \
  -d /opt/ansible
```

## 场景对比

### 何时使用 ansible-pull

✓ **大规模环境**（数百台以上主机）  
✓ **分布式部署**（节点遍布多个数据中心）  
✓ **无中央控制节点**（点对点自主管理）  
✓ **定时修复**（compliance、drift detection）  
✓ **网络隔离**（节点无法接收控制节点连接）  

### 何时使用 ansible-playbook

✓ **少量主机**（几十台）  
✓ **实时部署**（变更需立即生效）  
✓ **临时操作**（一次性任务）  
✓ **集中管理**（更好的审计和控制）  
✓ **复杂编排**（跨主机协调）  

## 常见问题

### Q: ansible-pull 和 Puppet/Chef 的 pull agent 有何区别？
A: ansible-pull 是轻量级脚本，每次执行都重新运行 Playbook；Puppet/Chef 有专门的 agent 服务。ansible-pull 更灵活，但需要更多的幂等性设计。

### Q: 如何处理 Playbook 执行失败？
A: 
- 用 `--force` 强制执行（忽略 git 更新失败）
- 用 `ignore_errors: yes` 在 Playbook 中处理失败
- 配置日志收集和告警

### Q: 大规模环境如何避免 Git 被击垮？
A: 
- 使用 `-s 60` 随机延迟，分散请求
- 使用 `-o` 仅在仓库更新时执行
- 考虑部署内部 Git mirror
- 增加 Git 服务器容量

## 提示

- **版本控制**：所有配置都在 Git 中，便于审计、回滚、协作
- **幂等性**：确保 Playbook 多次执行结果相同（关键！）
- **日志聚合**：用 fetch 模块或日志系统（ELK）收集执行结果
- **测试**：在小规模环境先验证，再推向生产
- **监控告警**：监控 cron 执行状态、git 更新、playbook 失败等
