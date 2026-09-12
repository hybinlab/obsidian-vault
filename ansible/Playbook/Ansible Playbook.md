---
publish: true
---
## ansible-playbook 剧本执行

`ansible-playbook` 是执行 Ansible **Playbook** 的核心工具，用于配置管理、应用部署、故障排查等复杂场景。相比 `ansible` 临时命令，Playbook 支持更复杂的逻辑、条件、循环和变量。

## 基本用法

```bash
# 执行单个 playbook
ansible-playbook site.yml

# 执行多个 playbook（按顺序）
ansible-playbook site.yml database.yml

# 指定清单文件
ansible-playbook -i inventory.ini site.yml

# 指定特定主机组
ansible-playbook -i inventory.ini -l webservers site.yml
```

## 常用参数

### 清单和主机选择

|参数|功能|
|---|---|
|-i / --inventory|指定清单文件路径|
|-l / --limit|进一步限定目标主机范围（子集），支持通配符|
|--list-hosts|列出将被操作的主机列表（不执行）|

```bash
# 列出 webservers 组中的所有主机
ansible-playbook -i inventory.ini -l webservers --list-hosts site.yml

# 仅对 web1 和 web2 执行
ansible-playbook site.yml -l "web1,web2"

# 排除某些主机
ansible-playbook site.yml -l "all:!db_servers"
```

### 任务执行控制

|参数|功能|
|---|---|
|-t / --tags|仅运行带有特定标签的任务|
|--skip-tags|跳过带有特定标签的任务|
|--start-at-task|从某个任务开始执行（之前的跳过）|
|--step|逐步执行，每个任务前确认|
|--list-tags|列出 playbook 中所有可用标签|
|--list-tasks|列出 playbook 中将执行的所有任务|

```bash
# 仅运行标签为 "install" 的任务
ansible-playbook site.yml -t install

# 跳过 "debug" 标签的任务
ansible-playbook site.yml --skip-tags debug

# 列出所有可用标签
ansible-playbook site.yml --list-tags

# 列出所有将执行的任务（不实际执行）
ansible-playbook site.yml --list-tasks

# 从特定任务开始执行
ansible-playbook site.yml --start-at-task "Install packages"

# 逐步执行（每个任务前询问）
ansible-playbook site.yml --step
```

### 权限提升

| 参数                     | 功能                     |
| ---------------------- | ---------------------- |
| -b / --become          | 以提升的权限运行（通常是 sudo）     |
| -K / --ask-become-pass | 提示输入提权密码               |
| --become-user          | 指定提权目标用户（默认 root）      |
| --become-method        | 指定提权方式（sudo、su、doas 等） |

```bash
# 以 sudo 权限执行（假设无密码 sudo）
ansible-playbook site.yml -b

# 执行前提示输入 sudo 密码
ansible-playbook site.yml -b -K

# 以特定用户身份执行
ansible-playbook site.yml -b --become-user=deploy

# 使用 su 而非 sudo
ansible-playbook site.yml -b --become-method=su -K
```

### 认证方式

|参数|功能|
|---|---|
|-k / --ask-pass|提示输入 SSH 密码|
|--private-key / -e|指定 SSH 私钥文件路径|
|-u / --user|指定远程连接用户|

```bash
# 使用密钥认证
ansible-playbook site.yml --private-key=~/.ssh/id_rsa

# 使用密码认证
ansible-playbook site.yml -k

# 指定连接用户
ansible-playbook site.yml -u deploy

# 结合多个选项
ansible-playbook site.yml -u deploy -b -K --private-key=~/.ssh/deploy_key
```

### 检查和调试

|参数|功能|
|---|---|
|-C / --check|检查模式（dry-run），预览会发生的改动但不实际执行|
|-D / --diff|显示文件变更的 diff 详情|
|--syntax-check|仅检查 playbook 语法，不执行|
|-v / -vv / -vvv / -vvvv|调试输出详细程度|

```bash
# 运行检查模式，查看会执行什么
ansible-playbook site.yml -C

# 检查模式 + diff 显示具体变更
ansible-playbook site.yml -C -D

# 仅检查语法（快速验证）
ansible-playbook site.yml --syntax-check

# 详细调试输出
ansible-playbook site.yml -vvv

# 检查模式 + 详细输出
ansible-playbook site.yml -C -vvv
```

### 并发和性能

|参数|功能|
|---|---|
|-f / --forks|并行进程数（默认 5）|

```bash
# 增加并发进程数以加快执行
ansible-playbook site.yml -f 10

# 串行执行（谨慎使用，会很慢）
ansible-playbook site.yml -f 1
```

### Vault 加密

|参数|功能|
|---|---|
|--vault-id|指定 Vault 密钥文件或提示输入密码|
|--vault-password-file|指定 Vault 密码文件路径|

```bash
# 执行包含加密变量的 playbook（提示输入密码）
ansible-playbook site.yml --vault-id @prompt

# 使用密钥文件
ansible-playbook site.yml --vault-password-file=~/.vault_pass
```

## 实战例子

### 例子1：选择性执行任务

```bash
# Playbook 中的标签示例
cat > deploy.yml << EOF
---
- hosts: webservers
  tasks:
    - name: Install packages
      yum:
        name: nginx
        state: present
      tags:
        - install

    - name: Configure nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      tags:
        - config

    - name: Start nginx
      service:
        name: nginx
        state: started
      tags:
        - start

    - name: Debug info
      debug:
        msg: "Deployment complete"
      tags:
        - debug
EOF

# 仅执行 install 和 config
ansible-playbook deploy.yml -t install,config

# 跳过 debug 标签
ansible-playbook deploy.yml --skip-tags debug
```

### 例子2：灰度发布（限定主机）

```bash
# 先在单个主机上测试
ansible-playbook site.yml -l web1

# 再在整个 webservers 组上执行
ansible-playbook site.yml -l webservers

# 排除某个主机
ansible-playbook site.yml -l "all:!db_server_1"
```

### 例子3：检查模式验证

```bash
# 先用检查模式看会做什么改动
ansible-playbook deploy.yml -C -D

# 确认无误后真实执行
ansible-playbook deploy.yml
```

### 例子4：逐步确认执行

```bash
# 用 --step 逐任务确认，每个任务前暂停询问
ansible-playbook deploy.yml --step

# 输出示例：
# TASK [Install packages] *****
# Perform task: Install packages (y/n/c):
```

### 例子5：从特定任务继续

```bash
# 假设前面某个任务失败了，修复后从该任务继续
ansible-playbook deploy.yml --start-at-task "Configure nginx"
```

### 例子6：完整的安全执行流程

```bash
# 1. 检查语法
ansible-playbook site.yml --syntax-check

# 2. 列出将执行的任务
ansible-playbook site.yml --list-tasks

# 3. 用检查模式预演
ansible-playbook site.yml -C -D

# 4. 真实执行（带详细输出以便问题排查）
ansible-playbook site.yml -v
```

## Playbook vs Ansible 临时命令

| 特点 | ansible 命令 | ansible-playbook |
|------|------------|-----------------|
| 适用场景 | 单次临时操作 | 复杂的配置管理、部署 |
| 支持逻辑 | 基础模块调用 | 条件、循环、变量、处理程序 |
| 幂等性 | 需手动保证 | 内置支持 |
| 代码复用 | 差 | 很好（Role、Handler、模板） |
| 标签支持 | ✗ | ✓ |
| 版本控制 | 不便 | 便于 Git 管理 |
| 学习成本 | 低 | 高 |

## 常见工作流

```bash
# 1. 开发 playbook
vim site.yml

# 2. 检查语法
ansible-playbook site.yml --syntax-check

# 3. 预演（检查模式）
ansible-playbook site.yml -C -D -l test_host

# 4. 测试执行（仅某个主机）
ansible-playbook site.yml -l test_host -v

# 5. 生产执行
ansible-playbook site.yml -l production -v

# 6. 事后验证
ansible-playbook verify.yml -l production
```

## 性能优化

```bash
# 增加并发数（在硬件允许的范围内）
ansible-playbook site.yml -f 20

# 异步执行长任务（Playbook 中配置）
# 在 task 中加入：
# async: 300          # 300秒超时
# poll: 0             # 不轮询结果，立即返回

# 使用 include_tasks 按需加载（减少内存占用）
```

## 提示

- **标签命名规范**：使用清晰的标签如 `install`、`config`、`start`、`debug` 便于选择性执行
- **检查模式很有用**：执行前先 `-C` 预演，避免意外修改
- **版本控制**：将 playbook 纳入 Git，便于追踪变更和回滚
- **测试环境**：在生产环境前，先在测试环境验证 playbook
- **日志记录**：用 `-vvv` 或配置日志输出，便于事后审计
