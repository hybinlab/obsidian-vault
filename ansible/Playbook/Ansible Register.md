---
publish: true
---
## Register（捕获任务结果）

`register` 把一个 task 的执行结果存进一个变量，供后续 task 使用——这是 Ansible 里"上一步做了什么、结果怎样"传递给"下一步该怎么做"的核心机制，`when` 条件分支、循环结果处理都建立在它上面。

## 基本用法

```yaml
- name: 执行命令并捕获输出
  ansible.builtin.shell: /usr/bin/foo
  register: foo_result
  ignore_errors: true      # 不加这个，命令失败会直接中断整个 playbook

- name: 用上一步的结果做判断
  ansible.builtin.shell: /usr/bin/bar
  when: foo_result.rc == 5
```

## 返回数据结构里的常用字段

| 字段 | 含义 |
|------|------|
| `rc` | 返回码，`0` 通常表示成功 |
| `stdout` | 标准输出（原始字符串，可能带换行符） |
| `stdout_lines` | 标准输出按行拆分成的列表，`debug` 打印更整齐 |
| `stderr` / `stderr_lines` | 标准错误输出，字符串/列表两种形式同 stdout |
| `changed` | 这个 task 是否被判定为"发生了变化"（结合 `changed_when` 使用） |
| `failed` | 这个 task 是否失败 |
| `results` | **循环场景专属**，是一个列表，每一项对应一次循环迭代的结果 |

```yaml
- name: 打印捕获到的完整结构（调试用）
  ansible.builtin.debug:
    var: foo_result
```

不确定某个字段具体长什么样时，先用 `debug` 把整个 `register` 变量打印出来，比翻文档猜字段名更快。

## 常见使用场景

### 判断上一步执行状态（配合 when）

```yaml
- name: 检查服务状态
  ansible.builtin.command: systemctl is-active myapp
  register: service_status
  failed_when: false     # 命令返回非 0 是正常情况（服务没在跑），不该让 task 报错中断
  changed_when: false     # 这只是查询，不改变任何状态

- name: 服务没在跑才启动
  ansible.builtin.service:
    name: myapp
    state: started
  when: service_status.rc != 0
```

更语义化的写法是用 Jinja2 Tests（详见 [[ansible/Playbook/Ansible Conditionals.md]]）：

```yaml
when: service_status is failed
when: service_status is succeeded
when: service_status is skipped
when: service_status is changed
```

### 循环中使用 register（结果会是 results 数组）

```yaml
- name: 循环执行命令
  ansible.builtin.shell: "echo {{ item }}"
  loop:
    - "one"
    - "two"
  register: echo_result

- name: 检查每次循环的返回码
  ansible.builtin.fail:
    msg: "命令 {{ item.cmd }} 执行失败"
  when: item.rc != 0
  loop: "{{ echo_result.results }}"
```

详见 [[ansible/Playbook/Ansible Loops.md]] 的 register 结合小节。

### 判断文件/目录状态（配合 stat 模块）

```yaml
- name: 检查文件是否存在
  ansible.builtin.stat:
    path: /etc/myapp/installed.flag
  register: install_flag

- name: 只有还没装过才执行安装
  ansible.builtin.shell: /opt/myapp/install.sh
  when: not install_flag.stat.exists
```

`stat` 模块返回的 `.stat` 字段里还有 `exists`、`isdir`、`size`、`mode` 等一大堆文件属性，比自己写 `test -f` 判断更结构化。

## 注意事项

- **`register` 变量只存在于当前 playbook 运行的内存里**，不会跨多次 `ansible-playbook` 执行持久化，也不能跨 host 共享（每台主机各自独立捕获自己的结果）
- **失败或被跳过的 task 依然会注册变量**，只是对应字段会记录相应状态（比如 `failed: true` 或者整体是空结构），不是"没跑就没有这个变量"——所以拿 `register` 变量做 `when` 判断前，最好先用 `debug` 确认过结构，避免因为 task 被跳过导致字段缺失而报错
- **要用 `register` 就通常要配 `ignore_errors: true` 或 `failed_when: false`**：默认情况下，一个 task 失败会直接中断整个 playbook 执行，如果你的意图是"跑一下这个命令，看结果再决定下一步"，必须显式告诉 Ansible 不要在这一步就中断

## 提示

- 命令类的检查（`command`/`shell`）配合 `register` 时，几乎总要搭配 `changed_when: false`（这只是查询不是改动）和/或 `failed_when: false`（不希望非 0 返回码就中断），三者是常见组合拳
- 优先用 `stat` 模块判断文件状态，而不是 `shell: test -f xxx` 再解析返回码——前者是声明式的结构化数据，后者要自己处理边界情况

## 相关笔记

- [[ansible/Playbook/Ansible Conditionals.md]] — register 结果配合 when 分支判断，及 is failed/succeeded/skipped/changed 语法
- [[ansible/Playbook/Ansible Loops.md]] — 循环中使用 register，results 数组的用法
- [[ansible/Ansible 模块.md]] — command vs shell，两者都不幂等，常用 register 配合处理
