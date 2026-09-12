---
publish: true
---
## Conditionals（when 条件判断）

`when` 用来控制一个 Task **要不要执行**。条件不满足时，Ansible 直接跳过这个 task（显示 `skipping`），不会尝试执行，也不会去检查目标状态——这是 [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] 中的第八个进阶主题。

## 基本语法

```yaml
- name: 仅在 Ubuntu 系统上安装 unattended-upgrades
  ansible.builtin.apt:
    name: unattended-upgrades
    state: present
  when: ansible_distribution == "Ubuntu"
```

**注意**：`when` 后面直接写 Jinja2 表达式，**不需要**加 `{{ }}`——这是 `when`/`until`/`failed_when`/`changed_when` 这类关键字的特殊语法糖，Ansible 会自动把它当表达式求值，加了 `{{ }}` 反而可能出问题。

```yaml
when: ansible_distribution == "Ubuntu"        # 正确
when: "{{ ansible_distribution == 'Ubuntu' }}"  # 不推荐，虽然某些情况能跑，但容易踩坑
```

## 写法：ansible_facts['xxx'] vs ansible_xxx

官方文档现在统一用 `ansible_facts['distribution']` 这种写法，不是本文档其他地方顺手写的 `ansible_distribution`：

```yaml
when: ansible_facts['os_family'] == "Debian"          # 官方推荐写法
when: ansible_distribution == "Ubuntu"                  # 老写法，仍能用，但已被标记废弃
```

这和之前 [[ansible/踩坑记录/Ansible Docker Host 部署踩坑记录.md]] 里实际碰到的 `INJECT_FACTS_AS_VARS` 废弃警告是同一件事——`ansible_xxx` 这种不带 `ansible_facts` 前缀、直接访问的写法，未来 `ansible-core 2.24` 会移除。新写的 playbook 一律用 `ansible_facts['xxx']`，本篇后面的例子为了简洁沿用了旧写法，实际使用时自行替换。

## 常用判断场景

### 按发行版分支

```yaml
- name: Ubuntu 系专属任务
  ansible.builtin.apt:
    name: unattended-upgrades
    state: present
  when: ansible_distribution == "Ubuntu"

- name: RHEL 系专属任务
  ansible.builtin.yum:
    name: yum-cron
    state: present
  when: ansible_distribution in ["CentOS", "RedHat"]
```

### 按主机名/分组分支

```yaml
- name: 只在指定主机上执行
  ansible.builtin.apt:
    name: docker-compose
    state: present
  when: inventory_hostname == "docker-host"

- name: 只对某个组内的主机执行
  ansible.builtin.debug:
    msg: "这是数据库服务器"
  when: inventory_hostname in groups['db_servers']
```

### 组合条件（and / or / not）

```yaml
- name: 同时满足多个条件
  ansible.builtin.apt:
    name: nginx
    state: present
  when:
    - ansible_distribution == "Ubuntu"
    - ansible_distribution_major_version | int >= 22

# 上面这种"列表形式"等价于 and，多个条件必须同时满足
```

```yaml
- name: 满足任一条件即可（or）
  ansible.builtin.debug:
    msg: "生产或预发环境"
  when: env == "prod" or env == "staging"

- name: 取反（not）
  ansible.builtin.apt:
    name: htop
    state: absent
  when: not (env == "prod")
```

### 基于 register 结果分支（和 register 配合，最常用的组合）

```yaml
- name: 检查某个文件是否存在
  ansible.builtin.stat:
    path: /etc/myapp/installed.flag
  register: install_flag

- name: 只有还没装过才执行安装
  ansible.builtin.shell: /opt/myapp/install.sh
  when: not install_flag.stat.exists
```

```yaml
- name: 执行一个可能失败的检查
  ansible.builtin.command: systemctl is-active myapp
  register: service_status
  failed_when: false      # 不让这个检查本身导致 task 失败中断
  changed_when: false

- name: 服务没在跑才启动
  ansible.builtin.service:
    name: myapp
    state: started
  when: service_status.rc != 0
```

### 判断任务执行状态（is failed / succeeded / skipped / changed）

`register` 捕获的不只是 `rc`/`stdout` 这些字段，还能直接判断这个 task 整体的执行状态，这是专门的 Jinja2 Tests 语法：

```yaml
- name: 执行一个可能失败的命令
  ansible.builtin.command: /bin/false
  register: result
  ignore_errors: true      # 不加这个，task 失败会直接中断整个 playbook

- name: 只在上一步失败时执行
  ansible.builtin.debug:
    msg: "上一步失败了，执行补救"
  when: result is failed

- name: 只在上一步成功时执行
  ansible.builtin.debug:
    msg: "上一步成功了"
  when: result is succeeded

- name: 只在上一步被跳过时执行
  ansible.builtin.debug:
    msg: "上一步被跳过了"
  when: result is skipped

- name: 只在上一步真的产生变化时执行
  ansible.builtin.debug:
    msg: "上一步 changed 了"
  when: result is changed
```

比自己手动判断 `result.rc != 0` 更语义化、更不容易写错。

### 判断变量是否已定义

```yaml
- name: 只在变量存在时执行
  ansible.builtin.debug:
    msg: "custom_port = {{ custom_port }}"
  when: custom_port is defined

- name: 变量未定义时给默认值（用 default 过滤器更常见）
  ansible.builtin.debug:
    msg: "端口是 {{ custom_port | default(8080) }}"
```

## 与 Loop 结合使用

`when` 和 `loop` 一起用时，条件是**对每一项循环单独求值**的，不是对整个循环判断一次：

```yaml
- name: 只处理大于 5 的项
  ansible.builtin.command: echo {{ item }}
  loop: [0, 2, 4, 6, 8, 10]
  when: item > 5
  # 实际效果：0/2/4 被 skip，6/8/10 才真正执行
```

循环变量本身可能未定义时，给个默认空列表避免报错：

```yaml
- name: 循环变量未定义时整个 task 跳过，而不是报错
  ansible.builtin.command: echo {{ item }}
  loop: "{{ mylist | default([]) }}"
  when: item > 5
```

## 与 import_tasks / include_tasks 结合使用（容易踩坑的区别）

这是官方文档专门强调的一个坑：`when` 加在 `import_tasks` 还是 `include_tasks` 上，行为完全不同。

**`import_tasks`（静态导入）**：条件会被**复制应用到被导入文件里的每一个 task**：

```yaml
# main.yml
- import_tasks: other_tasks.yml
  when: x is not defined

# other_tasks.yml —— 里面的每个 task 实际上都被加上了这个 when
- name: Set a variable
  ansible.builtin.set_fact:
    x: foo
  # 隐式带上了 when: x is not defined

- name: Print a variable
  ansible.builtin.debug:
    var: x
  # 同样隐式带上了 when: x is not defined
```

**`include_tasks`（动态包含）**：条件只判断"要不要执行这个 include 动作本身"，**不会传导**到被包含文件里的每个 task：

```yaml
# main.yml
- include_tasks: other_tasks.yml
  when: x is not defined

# other_tasks.yml —— 一旦 include 被执行，里面的 task 不受这个 when 限制，正常全部跑
- name: Set a variable
  ansible.builtin.set_fact:
    x: foo

- name: Print a variable
  ansible.builtin.debug:
    var: x
```

**记忆技巧**：`import` 是编译期静态展开（条件跟着一起复制粘贴到每个 task），`include` 是运行期动态判断（条件只管"要不要走进这个文件"，走进去之后就是走进去了，不再逐条二次判断）。

## 应用到整个 Play / Block

`when` 不止能加在单个 task 上，也能加在 `block`（把多个 task 打包）上，一次性控制一组任务：

```yaml
- name: 一组只在 Ubuntu 上执行的任务
  block:
    - name: 安装 A
      ansible.builtin.apt:
        name: package-a
        state: present
    - name: 安装 B
      ansible.builtin.apt:
        name: package-b
        state: present
  when: ansible_distribution == "Ubuntu"
```

**注意**：`when` 加在 `roles:` 引用上时，会作用于这个角色里的**每一个** task，不是只作用于角色本身：

```yaml
roles:
  - role: nginx_setup
    when: ansible_distribution == "Ubuntu"
```

## 常见判断依据来源

| 判断依据 | 例子 |
|---------|------|
| Facts（系统信息） | `ansible_distribution`、`ansible_distribution_release`、`ansible_architecture` |
| Inventory 相关 | `inventory_hostname`、`groups['组名']`、`group_names` |
| 之前 task 的执行结果 | `register` 捕获的变量，如 `result.rc`、`result.stdout`、`result.stat.exists` |
| 自定义变量 | 在 `vars:`/`host_vars`/`group_vars` 里定义的任意变量 |
| 变量存在性 | `变量名 is defined` / `变量名 is undefined` |

## 类型转换陷阱（容易踩坑）

条件判断里最常见的报错来源：**类型不匹配**，看起来一样的值实际比较结果是 false。

```yaml
# 陷阱：返回码 result.rc 实际是整数，和字符串 "127" 比较永远是 false
when: result.rc == "127"      # ❌ 大概率判断错误

# 正确：明确按整数比较
when: result.rc == 127        # ✓

# 陷阱：版本号这类 Facts 有时是字符串，直接数值比较可能出错
when: ansible_facts['lsb']['major_release'] >= 6         # ❌ 字符串比较，结果可能不符合预期

# 正确：显式转成整数再比较
when: ansible_facts['lsb']['major_release'] | int >= 6   # ✓

# 陷阱：自定义变量如果来自命令行/环境变量，即便写的是 true/false，类型也可能是字符串
when: monumental                # ❌ 如果 monumental 是字符串 "yes"，不一定按预期工作

# 正确：显式转布尔
when: monumental | bool         # ✓
```

**规律**：整数比较用 `| int` 强制转换，布尔判断用 `| bool` 强制转换，字符串比较判断空值用 `== ""`。不确定类型时，宁可多转一次。

## 调试条件表达式

条件判断结果不符合预期时，用 `debug` 直接打印表达式的求值结果，比反复改 `when` 猜哪里错了更快：

```yaml
- name: 看原始值
  ansible.builtin.debug:
    var: bar_status.rc

- name: 看字符串比较的结果
  ansible.builtin.debug:
    var: bar_status.rc == "127"

- name: 看整数比较的结果
  ansible.builtin.debug:
    var: bar_status.rc == 127
```

两次 `debug` 输出对比一下，就能立刻看出是不是类型不匹配导致条件判断错了。

## 实战验证技巧

`skipping` 是 `when` 生效的直接证据，跑一次带对比条件的 playbook 就能验证语法有没有写对：

```bash
ansible-playbook site.yml -v
```

```
TASK [仅在 CentOS/RHEL 系统上安装 yum-cron] ***
skipping: [hybin]      # ← 说明条件判断为 false，task 被跳过

TASK [仅在 Ubuntu 系统上安装 unattended-upgrades] ***
changed: [hybin]        # ← 条件判断为 true，正常执行
```

如果所有机器条件都一样（比如你 homelab 里目前都是 Ubuntu），想直观看到"条件不满足会跳过"的效果，用 `inventory_hostname` 这种肯定会产生分支的条件更容易验证，比用清一色相同的 Facts 条件更直观。

## 提示

- `when` 判断为 `false` 时，这个 task 完全不会执行，连"检查目标状态"这一步都不会做——不要和 `changed_when`（task 已经执行完，只是重新定义"算不算 changed"）搞混，两者作用的时机完全不同
- 组合条件优先用列表形式（隐式 and），比一行写一堆 `and` 更易读
- 判断变量是否存在，用 `is defined`/`is undefined`，这是 Jinja2 的 **Tests** 语法（进阶主题索引里的另一项），和 Filters（`| default(...)`）搭配使用效果类似但语义不同

## 相关笔记

- [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] — 其他进阶主题一览
- [[ansible/Playbook/Ansible Templating.md]] — Jinja2 基础语法（`when` 表达式本质是 Jinja2 表达式）
- [[ansible/Playbook/Ansible Playbook 编写.md]] — 幂等性、state 概念
