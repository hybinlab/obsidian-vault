---
publish: true
---
## ansible-doc 模块和插件文档查询

`ansible-doc` 是一个**插件文档工具**，用于查看 Ansible 库中安装的模块、插件、角色等的详细文档。比手动查官网文档更快。

### 基本用法

```bash
# 查看某模块的完整文档
ansible-doc copy

# 查看模块参数说明（简洁格式）
ansible-doc -s copy

# 列出所有可用模块
ansible-doc -l

# 搜索关键词（如所有包含"yum"的模块）
ansible-doc -l | grep yum

# 生成可直接粘贴到 Playbook 的代码片段
ansible-doc -s yum

# 以 JSON 格式输出（便于解析）
ansible-doc -j copy
```

### 常用参数

|参数|功能|
|---|---|
|-l / --list|列出所有可用插件（默认列出模块）|
|-F / --list_files|显示插件名称和源文件位置|
|-s / --snippet|生成 Playbook 代码片段（包含常用参数）|
|-t / --type|指定插件类型（见下文）|
|-j / --json|输出为 JSON 格式|
|-M / --module-path|指定模块搜索路径|
|-v / --verbose|增加调试输出详细程度|
|-h / --help|显示帮助信息|

### 查询不同类型的插件

`-t` 参数用来查询不同类型的插件：

|类型|说明|例子|
|---|---|---|
|module|模块（默认）|`ansible-doc -l -t module` 或简写 `ansible-doc -l`|
|become|权限提升方法|`ansible-doc -l -t become`|
|callback|回调插件|`ansible-doc -l -t callback`|
|connection|连接方式|`ansible-doc -l -t connection`|
|filter|过滤器（Jinja2 函数）|`ansible-doc -l -t filter`|
|test|测试插件|`ansible-doc -l -t test`|
|role|角色|`ansible-doc -l -t role`|
|vars|变量插件|`ansible-doc -l -t vars`|
|inventory|库存插件|`ansible-doc -l -t inventory`|
|strategy|策略插件|`ansible-doc -l -t strategy`|

### 实战例子

```bash
# 查看 service 模块的完整文档
ansible-doc service

# 快速查看 user 模块的参数列表
ansible-doc -s user

# 生成 copy 模块的 Playbook 代码片段
ansible-doc -s copy
# 输出示例：
# - name: Copy files
#   ansible.builtin.copy:
#     src: 
#     dest:
#     backup:
#     owner:
#     group:
#     mode:

# 列出所有 filter 插件
ansible-doc -l -t filter

# 查看 json_query filter 的文档
ansible-doc -t filter json_query

# 列出并显示源文件位置
ansible-doc -l -F | head -20

# 查看 local 连接方式的文档
ansible-doc -t connection local

# JSON 格式输出，便于脚本解析
ansible-doc -j service | jq .
```

### 和模块查询命令的对比

| 工具 | 用途 | 输出格式 |
|------|------|---------|
| `ansible-doc -l` | 列出所有模块 | 纯文本列表 |
| `ansible-doc -s 模块名` | 查看参数和代码片段 | 代码片段 |
| `ansible-doc 模块名` | 查看完整文档 | 详细文档 |
| `ansible-doc -l \| grep` | 搜索关键词 | 过滤后的列表 |
| `man ansible 模块名` | 用 man 命令查看（某些系统可用） | man page 格式 |

### 常见使用流程

```bash
# 1. 先搜索有哪些模块可用
ansible-doc -l | grep file

# 2. 快速查看该模块的参数
ansible-doc -s lineinfile

# 3. 详细了解用法和示例
ansible-doc lineinfile

# 4. 生成代码片段到 Playbook
ansible-doc -s lineinfile >> my-playbook.yml
```

### 提示

- `ansible-doc` 显示的是**本地已安装**的插件文档，不同系统版本可能有差异
- 若找不到某个模块，检查是否已通过 Collections 安装
- 文档中的 `EXAMPLES` 部分最有参考价值，通常有实际使用案例
- 结合 `less` 分页查看长文档：`ansible-doc service | less`
