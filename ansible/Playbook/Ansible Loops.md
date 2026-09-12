---
publish: true
---
## Loops（循环）

`loop` 用来对一个列表里的每一项重复执行同一个 task，避免写多个重复 task。这是 [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] 中的第六个进阶主题。

## 先判断：真的需要 loop 吗？

很多模块（`apt`/`yum`/`user`/`file` 等）**本身就支持传列表参数**，这种情况下优先直接传列表，不要用 `loop`：

```yaml
# ❌ 不推荐：会循环调用三次 apt，效率差、日志啰嗦
- ansible.builtin.apt:
    name: "{{ item }}"
    state: present
  loop: [curl, git, vim]

# ✓ 推荐：只调用一次 apt，一条命令装完
- ansible.builtin.apt:
    name: [curl, git, vim]
    state: present
```

`loop` 真正该用的场景是：**模块本身不支持传列表参数**，比如 `user` 模块一次只能操作一个用户：

```yaml
- name: 循环创建多个用户
  ansible.builtin.user:
    name: "{{ item }}"
    state: present
    groups: wheel
  loop:
    - testuser1
    - testuser2
```

## 基本语法

### 简单列表

```yaml
- name: 添加多个用户
  ansible.builtin.user:
    name: "{{ item }}"
    state: present
  loop:
    - testuser1
    - testuser2
```

### 字典列表（每项有多个字段）

```yaml
- name: 添加多个用户，各自指定所属组
  ansible.builtin.user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
    state: present
  loop:
    - { name: 'testuser1', groups: 'wheel' }
    - { name: 'testuser2', groups: 'root' }
```

### 循环字典本身（用 dict2items 过滤器）

```yaml
- name: 遍历一个字典
  ansible.builtin.debug:
    msg: "{{ item.key }}: {{ item.value.ip_address }}"
  loop: "{{ server_configs | dict2items }}"
  vars:
    server_configs:
      web_01:
        ip_address: "10.1.1.50"
      web_02:
        ip_address: "10.1.1.51"
```

## loop 和旧的 with_items 的关系

`with_items`/`with_dict`/`with_fileglob` 这类是 Ansible 2.5 之前的旧语法，`loop` 是官方现在推荐的统一写法。**两者不要混用**，迁移时注意一个关键区别：

- `with_items` 会**自动展平**一层嵌套列表
- `loop` **不会自动展平**，需要显式加 `| flatten(1)` 过滤器

```yaml
# 旧写法：with_items 自动展平
with_items:
  - 1
  - [2, 3]
  - 4
# 实际效果等价于遍历 [1, 2, 3, 4]

# 新写法：loop 需要显式展平
loop: "{{ [1, [2, 3], 4] | flatten(1) }}"
```

**迁移速查表**：

| 旧语法 | 新语法 |
|--------|--------|
| `with_list` | `loop` |
| `with_items` | `loop` + `\| flatten(levels=1)` |
| `with_dict` | `loop` + `\| dict2items` |
| `with_sequence` | `loop` + `range(...)` |
| `with_nested` | `loop` + `\| product(...)` |
| `with_fileglob` | 官方建议保留 `with_fileglob`，`loop` 处理文件查找类场景反而更麻烦 |

## loop_control：控制循环行为

### label：简化冗长输出

循环项是复杂字典时，默认输出会把整个字典都打印出来，很乱。用 `label` 只显示关键字段：

```yaml
- name: 创建服务器
  digital_ocean:
    name: "{{ item.name }}"
    state: present
  loop:
    - { name: server1, disks: 3gb, region: nyc }
    - { name: server2, disks: 5gb, region: sfo }
  loop_control:
    label: "{{ item.name }}"    # 输出只显示 server1/server2，不显示整个字典
```

### pause：循环间加延迟

```yaml
- name: 逐个创建服务器，避免瞬间并发请求触发限流
  community.digitalocean.digital_ocean:
    name: "{{ item }}"
    state: present
  loop:
    - server1
    - server2
  loop_control:
    pause: 3    # 每次迭代间隔 3 秒
```

### index_var：获取当前循环的索引

```yaml
- name: 打印带索引的水果列表
  ansible.builtin.debug:
    msg: "{{ item }} 的索引是 {{ my_idx }}"
  loop:
    - apple
    - banana
    - pear
  loop_control:
    index_var: my_idx    # 索引从 0 开始
```

### loop_var：嵌套循环时重命名，避免变量冲突

`include_tasks`/`import_tasks` 里再套一层 `loop` 时，内外两层默认都叫 `item`，会互相覆盖，必须用 `loop_var` 给外层改名：

```yaml
# main.yml —— 外层循环
- include_tasks: inner.yml
  loop: [1, 2, 3]
  loop_control:
    loop_var: outer_item    # 外层改名为 outer_item，避免和内层 item 冲突

# inner.yml —— 内层循环
- ansible.builtin.debug:
    msg: "外层={{ outer_item }} 内层={{ item }}"
  loop: [a, b, c]
```

## 与 register 结合，捕获每次循环的结果

```yaml
- name: 循环执行命令并捕获所有结果
  ansible.builtin.shell: "echo {{ item }}"
  loop:
    - "one"
    - "two"
  register: echo_result
```

`register` 在循环场景下，捕获到的是一个 `results` 数组，每一项对应一次循环迭代的结果：

```yaml
- name: 检查每次循环的返回码，非 0 就报错
  ansible.builtin.fail:
    msg: "命令 {{ item.cmd }} 执行失败"
  when: item.rc != 0
  loop: "{{ echo_result.results }}"
```

## until：条件重试（配合循环但语义不同）

`until` 不是遍历一个列表，是"重复执行同一个 task，直到满足条件为止"，常用于等待某个异步状态就绪：

```yaml
- name: 重试直到服务真正就绪
  ansible.builtin.shell: /usr/bin/check-status
  register: result
  until: result.stdout.find("all systems go") != -1
  retries: 5
  delay: 10
```

`until` 表达式和 `when` 一样不需要加 `{{ }}`。`retries` 是最大重试次数，`delay` 是每次重试间隔（秒）。

## 常见陷阱

- **循环变量未定义时报错**：给循环变量加 `| default([])`，避免变量不存在直接导致 task 报错，而是安全地跳过整个循环

```yaml
loop: "{{ mylist | default([]) }}"
```

- **loop 和 when 一起用**：条件是对每一项单独求值（详见 [[ansible/Playbook/Ansible Conditionals.md]] 的 Loop 结合小节），不是对整个循环判断一次

- **lookup 插件返回的是字符串不是列表**：某些 lookup（如 `fileglob`）直接放进 `loop` 可能不会按预期展开成列表，需要用 `query()`（推荐）或者给 `lookup()` 加 `wantlist=True`：

```yaml
# 可能不按预期工作
loop: "{{ lookup('fileglob', '*.txt') }}"

# 推荐写法
loop: "{{ query('fileglob', '*.txt') }}"
```

- **敏感数据别只靠 label 隐藏**：`loop_control.label` 只是控制屏幕输出好不好看，循环项里如果有密码，该用 `no_log: true` 才是真正防止泄露到日志里

## 提示

- 判断要不要用 `loop` 的第一原则：先看模块本身支不支持传列表参数，支持就别用 `loop`
- 迁移旧 playbook 时，`with_items` 换成 `loop` 记得手动加 `flatten(1)`，否则嵌套列表的行为会变
- 复杂的多层嵌套循环，优先考虑把数据结构改成一层字典/列表，而不是硬套多层 `loop`，可读性差太多

## 相关笔记

- [[ansible/Playbook/Ansible Playbook 进阶主题索引.md]] — 其他进阶主题一览
- [[ansible/Playbook/Ansible Conditionals.md]] — when 和 loop 结合使用
- [[ansible/Playbook/Ansible Templating.md]] — dict2items 等过滤器的 Jinja2 基础
