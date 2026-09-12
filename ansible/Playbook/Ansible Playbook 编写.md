---
publish: true
---
## Playbook 编写基础

Playbook 是用 YAML 编写的配置管理"剧本"。这篇笔记讲**怎么写** Playbook（YAML 结构、Play/Task 语法）；`ansible-playbook` 命令怎么**执行**它见 [[ansible/Playbook/Ansible Playbook.md]]。

## 核心结构：Play 和 Task

一个 Playbook 由一个或多个 **Play** 按顺序组成；每个 Play 至少包含 `hosts`（目标主机）和 `tasks`（要执行的任务列表）。

```yaml
---
- name: 更新 web 服务器                    # Play 描述（可选但强烈推荐）
  hosts: webservers                       # 目标主机组
  remote_user: root                       # 连接用户
  tasks:
    - name: 确保 apache 已安装并是最新版    # Task 描述
      ansible.builtin.yum:                # 模块名（推荐用完全限定名 FQCN）
        name: httpd
        state: latest

    - name: 确保 apache 正在运行
      ansible.builtin.service:
        name: httpd
        state: started
```

## 执行顺序

- **Play 之间**：从上到下顺序执行
- **Task 之间**：同一个 Play 内也是从上到下顺序执行
- 想跳过/只执行部分任务，用标签（tags），见 [[ansible/Playbook/Ansible Playbook.md]] 的 `-t`/`--skip-tags`

## 多个 Play（针对不同主机组）

一个文件里可以写多个 Play，分别配置不同的主机组，实现"一个 Playbook 管全部"：

```yaml
---
- name: 更新 web 服务器
  hosts: webservers
  tasks:
    - name: 安装 Apache
      ansible.builtin.yum:
        name: httpd
        state: latest

- name: 更新数据库服务器
  hosts: databases
  tasks:
    - name: 安装 PostgreSQL
      ansible.builtin.yum:
        name: postgresql
        state: latest
```

## 模块调用格式（FQCN）

现代 Ansible **推荐用完全限定集合名称（FQCN）**调用模块，格式为 `命名空间.集合.模块名`：

```yaml
tasks:
  - name: 用 FQCN 调用内置模块（推荐）
    ansible.builtin.copy:
      src: file.txt
      dest: /tmp/file.txt

  - name: 简写形式（旧写法，仍可用但不推荐在正式项目中用）
    copy:
      src: file.txt
      dest: /tmp/file.txt
```

内置模块的命名空间是 `ansible.builtin`；如果用的是 Collection 里的模块（见 [[ansible/Ansible Galaxy.md]]），命名空间是该 Collection 的名字，比如 `community.general.ufw`。

**为什么用 FQCN**：
- 避免不同 Collection 之间模块名冲突（比如多个 Collection 都提供叫 `user` 的模块）
- 明确知道这个任务依赖哪个 Collection，便于排查环境缺失依赖的问题

## Play 级别的常用参数

除了 `hosts` 和 `tasks`，Play 层面还能配置：

|参数|作用|
|---|---|
|name|Play 的描述，会显示在执行输出里|
|hosts|目标主机组（对应 Inventory 中的组名或主机模式）|
|remote_user|连接远程主机用的用户|
|become|是否提权执行（同 `-b`）|
|become_user|提权后的目标用户|
|connection|连接方式（默认 ssh，也可以 local）|
|gather_facts|是否收集主机信息（setup 模块），默认 yes|
|vars|定义 Play 级别的变量|
|tasks|要执行的任务列表|
|handlers|处理程序列表（被 `notify` 触发）|
|roles|引用的角色列表|

```yaml
---
- name: 完整配置示例
  hosts: webservers
  remote_user: deploy
  become: yes
  become_user: root
  gather_facts: yes
  vars:
    http_port: 8080
  tasks:
    - name: 安装 nginx
      ansible.builtin.yum:
        name: nginx
        state: present
```

## 幂等性（Idempotency）

Ansible 模块设计上大多是**幂等**的：重复执行同一个 Task，只有第一次真正改变了状态，之后再跑不会重复操作。

```yaml
# 这个任务无论跑多少次，结果都一样：httpd 已安装且是最新版
# 如果已经是最新版，Ansible 会跳过，报告 "ok" 而非 "changed"
- name: 确保 httpd 是最新版
  ansible.builtin.yum:
    name: httpd
    state: latest
```

这也是为什么应该优先用**声明式模块**（`yum`、`service`、`copy` 等），而不是 `command`/`shell` 直接跑命令——后者每次执行都会"changed"，无法准确反映是否真的做了改动。

### state 是幂等性的灵魂

`state` 参数是几乎所有资源类模块的统一语言，它定义的是**目标状态**，不是**要执行的动作**：

- `file`: state 决定文件/目录/链接存在与否、是什么类型
- `user`: state 决定用户存在与否（present/absent）
- `service`: state 决定服务在跑还是停着（started/stopped/restarted）
- `yum`/`apt`: state 决定包装没装、是不是最新（present/absent/latest）
- `cron`: state 决定这条定时任务在不在（present/absent）

正因为任务描述的是"最终状态应该是什么"，而不是"去执行删除/创建这个动作"，Ansible 才能在执行前对比现状和目标状态，一致就跳过。这就是幂等性的来源。

反过来，`command`/`shell` 没有 `state` 这个概念，Ansible 不知道"目标状态"是什么，只能"跑了就算跑了"，所以永远不幂等（见 [[ansible/Ansible 模块.md]] 的 command vs shell 对比）。

### 常见 state 取值速查

|模块|常见取值|
|---|---|
|通用基础值|`present`（存在）/ `absent`（不存在）—— 几乎所有资源类模块都支持|
|file|`file` / `directory` / `absent` / `link`（符号链接）/ `hard`（硬链接）/ `touch`（建空文件或更新时间戳）|
|yum / apt / dnf|`present` \| `installed`（已装，不管版本）/ `absent` \| `removed`（已卸载）/ `latest`（最新版）|
|service / systemd|`started`（运行）/ `stopped`（停止）/ `restarted`（重启，每次都触发）/ `reloaded`（重载配置，不整个重启）|
|user / group|`present` / `absent`|
|mount|`mounted`（挂载+写入 fstab）/ `unmounted`（卸载但留 fstab 条目）/ `absent`（卸载+删 fstab 条目）/ `present`（只写 fstab 不挂载）|
|lineinfile / blockinfile / cron|`present` / `absent`|

规律：`present`/`absent` 是通用的"存在与否"语言；服务类模块额外有"运行态"取值，因为服务不只是"存在"，还有"是否在跑"这个维度。具体某模块支持哪些值，`ansible-doc -s 模块名` 一查就知道。

## 编写建议和校验工具

```bash
# 写完先检查语法（不执行）
ansible-playbook site.yml --syntax-check

# 列出会执行哪些任务（不执行）
ansible-playbook site.yml --list-tasks

# 检查模式预演（不实际改动）
ansible-playbook site.yml --check

# 用 ansible-lint 做代码规范检查（需单独安装：pip install ansible-lint）
ansible-lint site.yml
```

`ansible-lint` 会检查一些常见问题：没用 FQCN、没写 `name`、用了危险的 `command`/`shell` 而不是专门模块、缩进问题等。

## 常见误区

- **忘记 `---` 开头**：YAML 文件建议以 `---` 开始，标记文档起始
- **缩进错误**：YAML 对缩进敏感，用空格不要用 Tab，同级元素缩进要对齐
- **每个 Task 都要写 `name`**：不写 `name` 也能跑，但排查问题时输出只会显示模块名，不直观
- **滥用 `command`/`shell`**：能用专门模块（`yum`、`copy`、`service`）就不要用 `command`/`shell`，前者幂等、后者每次都会显示 changed

## 相关笔记

- [[ansible/Playbook/Ansible Playbook.md]] — `ansible-playbook` 命令的执行参数（标签、检查模式、权限提升）
- [[ansible/Ansible 模块.md]] — 常用模块速查
- [[ansible/Ansible Inventory.md]] — hosts 对应的主机清单配置
- [[ansible/Ansible Galaxy.md]] — Collection 和 Role，FQCN 命名空间的来源
