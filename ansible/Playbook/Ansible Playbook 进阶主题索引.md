---
publish: true
---
## Playbook 进阶主题一览

来源：[Working with playbooks](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks.html) 官方索引页。这些是比 [[ansible/Playbook/Ansible Playbook 编写.md]] 更深入的主题，先列个索引存档，用到哪个再展开细节。

| 主题 | 一句话说明 |
|------|-----------|
| **Templating（Jinja2）** ✅ | Playbook 里用 `{{ }}` 语法渲染变量、写模板文件 — 详见 [[ansible/Playbook/Ansible Templating.md]] |
| **Filters** | 对变量做转换/处理，如格式化、取默认值、类型转换、数学运算 |
| **Tests** | 判断变量的状态，如是否已定义、版本比较、路径是否存在 |
| **Lookups** | 从外部数据源读值，如环境变量、文件内容、Vault 密码 |
| **Python3 in templates** | 模板中 Python3 相关的语法差异说明 |
| **Loops** ✅ | 循环执行任务，对一个列表里的每项重复相同操作（`loop`） — 详见 [[ansible/Playbook/Ansible Loops.md]] |
| **委托（Delegation）** | 控制某个任务实际在哪台机器上执行（而非默认的受管节点） |
| **条件判断（Conditionals）** ✅ | `when` 语句，根据条件决定任务是否执行 — 详见 [[ansible/Playbook/Ansible Conditionals.md]] |
| **Blocks** | 把多个任务打包成一组，统一加条件/错误处理/权限提升 |
| **Handlers** | 被 `notify` 触发的特殊任务，仅在前置任务"changed"时执行 |
| **错误处理** | 忽略失败（`ignore_errors`）、自定义"changed"判断逻辑等 |
| **Variables** | 变量类型、作用域、优先级、Facts（自动收集的主机信息） |
| **Roles** | 结构化组织 Playbook 的标准目录格式，便于复用 |
| **实践案例** | 持续部署、滚动升级（rolling update）等真实场景示例 |

> 另外补一个官方索引里没单独列、但用得极频繁的机制：**Register**（捕获任务结果），详见 [[ansible/Playbook/Ansible Register.md]]，是 Conditionals/Loops 判断分支的基础。

## 优先级建议（homelab 场景）

写实用 Playbook 最先会用到的：**Variables → Conditionals → Loops → Handlers**，这几个是家常便饭。其余（Templating/Filters/Lookups/Blocks/Delegation/Roles）随着 Playbook 复杂度提升，遇到具体需求时再单独深挖。
