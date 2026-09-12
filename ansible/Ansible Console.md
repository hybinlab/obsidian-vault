---
publish: true
---
## ansible-console 交互式命令行

`ansible-console` 是一个 **REPL（交互式命令行界面）**，可以针对选定的清单持续执行临时任务，而不必每次都键入完整的 `ansible` 命令。

### 启动

```bash
# 进入交互式会话，针对所有主机
ansible-console all

# 针对特定组
ansible-console webservers

# 针对特定模式（如所有 prod 开头的主机）
ansible-console "prod*"

# 指定库存文件
ansible-console -i inventory.ini all

# 开启提权和检查模式
ansible-console all -b -C
```

### 内置命令

在 `ansible-console` 内输入这些特殊命令来控制行为：

| 命令 | 功能 |
|------|------|
| `cd [pattern]` | 切换目标主机/组（支持模式匹配），如 `cd webservers` 或 `cd "prod*"` |
| `list` | 列出当前路径（`cd` 目录）中的所有可用主机 |
| `become` | 切换特权提升标志（on/off），等同于 `-b` 选项 |
| `!` | 强制使用 shell 模块执行命令（而非 command 模块） |
| `verbosity [num]` | 设置输出详细程度，如 `verbosity 3` 等同于 `-vvv` |
| `check [on\|off]` | 切换检查模式（演练模式） |
| `help` | 显示帮助信息 |
| `help [module_name]` | 查看某模块的帮助文档，如 `help copy` |
| `exit` 或 `quit` | 退出 ansible-console |

### 实际使用例子

```bash
$ ansible-console all
Welcome to ansible-console, version 2.10.0
[WARNING] Found variable using reserved name: ansible_version
Type help or ? for help.

> list                                    # 列出所有主机
192.168.10.20
192.168.10.21

> cd webservers                           # 切换到 webservers 组
> list
web1
web2

> ping                                    # 执行 ping 模块
> copy src=/tmp/file dest=/tmp/           # 执行 copy 模块
> shell "systemctl restart nginx"         # 执行 shell 命令（带引号）
> become                                  # 启用提权
> check on                                # 启用检查模式
> verbosity 3                             # 提升详细程度
> help setup                              # 查看 setup 模块帮助
> exit                                    # 退出会话
```

### 常用启动参数

这些参数和 `ansible` 命令相同：

|参数|作用|
|---|---|
|-i / --inventory|指定库存文件路径|
|-u / --user|指定远程连接用户|
|-k|手动输入 SSH 密码|
|-b / --become|启用提权（sudo）|
|-K|提示输入提权密码|
|-c / --connection|指定连接类型（如 ssh、local）|
|-T / --timeout|设置 SSH 连接超时时间|
|-f / --forks|并发进程数（默认 5）|
|-C / --check|启动时即启用检查模式|
|-D|启用 diff 模式，显示变更详情|
|-v / -vv / -vvv|调试输出详细程度|

### 使用场景

- **快速临时操作**：不需要编写 Playbook，直接在交互式会话中执行多个命令
- **交互式故障排查**：逐步执行命令，观察结果，动态调整下一步操作
- **学习和测试**：探索模块、测试命令语法，tab 键补全支持很方便
- **简单的一次性任务**：比编写 Playbook 更快速高效

### 和 `ansible` 命令的对比

| 特点 | ansible | ansible-console |
|------|---------|-----------------|
| 每条命令都要完整键入 | ✓ | ✗ |
| 保持持续会话 | ✗ | ✓ |
| 支持目标切换（cd） | ✗ | ✓ |
| Tab 补全 | ✗ | ✓ |
| 适合一次性命令 | ✓ | ✗ |
| 适合多个连续操作 | ✗ | ✓ |
