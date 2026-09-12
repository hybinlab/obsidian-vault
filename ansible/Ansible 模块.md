---
publish: true
---
## 常用模块速查

实际工作中常用的也就十来个。不必死记模块列表，记住查询方法最重要：

| 模块 | 用途 |
|------|------|
| **ping** | 检查 SSH 连接和 Python 是否可用 |
| **copy** | 复制文件到受管节点 |
| **template** | 复制模板文件（支持变量渲染）到受管节点 |
| **command** / **shell** | 执行命令（command 不支持管道等特殊字符；shell 支持） |
| **yum** | 安装、更新、卸载软件包（RHEL/CentOS） |
| **service** | 启动、停止、重启服务，查看服务状态 |
| **user** | 创建、修改、删除用户 |
| **file** | 设置文件权限、创建目录、软硬链接 |
| **lineinfile** | 修改文件内容（基于正则表达式逐行匹配） |
| **setup** | 收集受管节点系统信息和变量（自动执行） |
| **debug** | 输出信息用于调试（like `print()`） |

## 查询模块的方法

```bash
# 列出所有可用模块
ansible-doc -l

# 搜索关键词（如"yum"）
ansible-doc -l | grep yum

# 查看某模块的详细用法和示例
ansible-doc 模块名

# 查看模块的参数说明
ansible-doc -s 模块名
```

用多了自然就熟了。遇到新需求，直接搜索关键词，看 `ansible-doc 模块名` 的用法和示例就行。

详见 [[ansible/Ansible Doc.md]] — ansible-doc 工具的完整用法和参数参考。

## command vs shell

两者都是在受管节点上执行命令，区别在于**要不要经过 shell 解释器**：

|  | command | shell |
|---|---|---|
| 执行方式 | 直接调用程序，不经过 `/bin/sh` | 先扔给 `/bin/sh -c` 执行 |
| 管道 `\|`、重定向 `>`、通配符 `*`、`&&`、环境变量 `$HOME` | ❌ 不支持 | ✓ 支持 |
| 安全性 | 更安全，不存在 shell 注入风险 | 有 shell 注入风险（变量拼进命令要小心） |
| 幂等性 | ❌ 非幂等，每次都 `changed` | ❌ 非幂等，每次都 `changed` |

```yaml
# command：不支持管道，这样写要么报错要么把 | 当成参数传给 ps
- ansible.builtin.command: "ps aux | grep nginx"   # 不会按预期工作

# shell：支持管道
- ansible.builtin.shell: "ps aux | grep nginx"     # 正常工作
```

**判断标准**：没用到管道/重定向这些 shell 语法时，一律用 `command`（更安全）；只有确实需要 shell 特性时才用 `shell`。

两者都不是幂等的（每次执行都显示 `changed`），需要用 `changed_when` 手动修正判断逻辑，或者优先考虑有没有对应的声明式模块可以替代（比如 `useradd` 该用 `user` 模块），详见 [[ansible/Playbook/Ansible Playbook 编写.md]] 的幂等性小节。
