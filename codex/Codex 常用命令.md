---
title: Codex 常用命令
tags:
  - Codex
  - 命令笔记
updated: 2026-11-03
---

# Codex 常用命令

适用于 **Codex CLI**。根据 [OpenAI 官方命令文档](https://learn.chatgpt.com/docs/developer-commands?surface=cli#cli-command-overview) 整理，并使用本机 `codex-cli 0.164.0` 的 `--help` 核对终端命令。

`codex ...` 在系统终端运行；`/model`、`/status` 等在 Codex 会话输入框中使用。下文 `<SESSION_ID>`、`<MODEL>` 等为占位符，使用时替换为实际值，不保留尖括号。命令可用性随版本、账号和配置变化，以本机帮助及 `/` 菜单为准。

## 1. 高频命令速查

| 命令 | 用途 |
| --- | --- |
| `codex` | 在当前目录启动交互会话 |
| `codex "解释这个项目的目录结构"` | 启动会话并提交第一条任务 |
| `codex -C /path/to/project` | 指定工作目录 |
| `codex resume` | 从列表选择历史会话 |
| `codex resume --last` | 继续当前目录最近的会话 |
| `codex resume --all` | 在选择列表中显示其他目录的会话 |
| `codex fork --last` | 基于最近会话创建分支会话 |
| `codex exec "总结这个仓库"` | 非交互执行任务，别名 `codex e` |
| `codex review --uncommitted` | 审查尚未提交的改动 |
| `codex --search` | 启动会话并启用实时网页搜索 |
| `codex --version` | 查看本机版本，简写 `codex -V` |
| `codex --help` | 查看顶层帮助，子命令也可加 `--help` |

例如，直接在知识库目录开始整理笔记：

```bash
codex -C /root/obsidian-vault "按现有目录整理一份 Docker 排障 SOP"
```

## 2. 登录、更新与诊断

| 命令 | 用途 |
| --- | --- |
| `codex login` | 使用浏览器完成 ChatGPT 登录 |
| `codex login --device-auth` | 使用设备验证码登录，适合远程终端 |
| `codex login status` | 查看当前登录状态 |
| `codex logout` | 清除本地保存的登录凭据 |
| `codex update` | 更新 CLI；需要当前安装方式支持自更新 |
| `codex doctor` | 诊断安装、配置、认证和运行环境 |
| `codex doctor --summary` | 只显示诊断摘要 |

如果使用 API Key，并且已经设置 `OPENAI_API_KEY` 环境变量：

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

## 3. 启动参数与权限

| 参数示例 | 用途 |
| --- | --- |
| `-C /path/to/project` | 设置工作目录 |
| `-m <MODEL>` | 选择账号可用的模型；也可以进入会话后用 `/model` 选择 |
| `-i ./error.png` | 把图片附在第一条任务中 |
| `--search` | 使用实时网页搜索；普通本地会话默认使用缓存搜索 |
| `-s read-only` | 使用只读沙盒 |
| `-s workspace-write` | 允许在工作区等授权路径写入，仍受沙盒限制 |
| `-a on-request` | 由 Codex 判断何时请求人工批准 |
| `-a never` | 不弹出人工批准请求；被权限限制的操作仍会失败 |
| `--approve-for-me` | 使用工作区写入沙盒，并由自动审批审核权限请求 |
| `--add-dir /path/to/extra` | 增加可写目录，可以重复指定 |
| `--worktree` | 在新的托管 Git worktree 中开始任务，需要本地 Git 仓库 |
| `--no-alt-screen` | 在普通终端屏幕中显示，保留终端滚动记录 |
| `-c 'model_reasoning_effort="high"'` | 临时覆盖推理强度，模型需支持该值 |

日常编辑，按需请求批准：

```bash
codex -s workspace-write -a on-request
```

只读分析：

```bash
codex -s read-only "检查项目结构并说明可能的问题"
```

附带错误截图：

```bash
codex -i ./error.png "分析截图中的报错，并检查相关配置"
```

`--approve-for-me` 是单独的启动方式，不与 `--sandbox`、`--ask-for-approval` 混用。`-a never` 只控制审批，不会解除沙盒。参数组合参见[官方 CLI 参数说明](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。

用户配置通常位于 `~/.codex/config.toml`；可信项目还可以有 `.codex/config.toml`。`-c` 只覆盖本次运行的配置。已配置独立 profile 时，可用 `codex -p dev` 加载 `~/.codex/dev.config.toml`，设置了 `CODEX_HOME` 时则使用对应目录。详见[配置基础](https://learn.chatgpt.com/docs/config-file/config-basic)。

## 4. 会话内常用斜杠命令

先运行 `codex`，再在输入框里输入 `/` 选择命令。此处按用途摘选 CLI 命令，完整列表见[官方斜杠命令说明](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。

| 命令 | 用途 |
| --- | --- |
| `/status` | 检查当前模型、权限、工作目录和上下文使用情况 |
| `/model` | 选择模型及可用的推理强度 |
| `/permissions` | 调整本次会话的操作权限 |
| `/plan` | 切换到规划模式；可附带任务描述 |
| `/init` | 为当前目录生成 `AGENTS.md` 指令文件 |
| `/diff` | 查看工作区改动 |
| `/review` | 选择代码审查目标 |
| `/compact` | 压缩对话上下文，保留关键摘要 |
| `/new` | 在当前 CLI 中开始新对话 |
| `/clear` | 清空终端显示并开始新对话 |
| `/resume` | 选择并继续历史会话 |
| `/fork` | 从当前对话创建分支会话 |
| `/rename` | 为当前会话命名，方便之后查找 |
| `/archive` | 归档当前会话 |
| `/mcp` | 查看当前配置的 MCP 工具 |
| `/skills` | 浏览和使用技能 |
| `/plugins` | 浏览及管理插件 |
| `/agents` | 打开会话与 agent 管理界面 |
| `/subagents` | 切换查看当前任务的子 agent |
| `/ps` | 查看后台终端及最近输出 |
| `/stop` | 停止当前会话的后台终端任务 |
| `/copy` | 选择要复制的回复或代码块 |
| `/config` | 调整终端界面偏好 |
| `/exit` 或 `/quit` | 退出 CLI |

知识库已有 `AGENTS.md`，日常整理时可以直接使用其中约定。`/compact` 适合继续同一任务；换一个独立主题时使用 `/new`。

## 5. 恢复、分支与归档会话

| 命令 | 用途 |
| --- | --- |
| `codex resume <SESSION_ID>` | 恢复指定会话，也支持会话名称 |
| `codex resume --last "继续补全验证步骤"` | 继续最近会话并发送新指令 |
| `codex resume --last --all` | 跨目录选择最近的会话 |
| `codex fork <SESSION_ID>` | 以指定会话为起点，尝试另一条思路 |
| `codex archive <SESSION_ID>` | 将已完成会话归档 |
| `codex unarchive <SESSION_ID>` | 恢复已归档会话 |

`resume` 继续原会话，`fork` 创建新会话。会话分支本身不会隔离工作区文件；需要独立文件目录时，使用支持 `--worktree` 的新任务或分支任务。官方说明中 `resume` 不支持 `--worktree`。

## 6. 非交互执行与保存结果

`codex exec` 适合一次性任务和脚本。普通文本模式下，进度写入 `stderr`，最后回复写入 `stdout`；`--json` 则将 `stdout` 改为 JSONL 事件流。见[官方非交互模式文档](https://learn.chatgpt.com/docs/non-interactive-mode)。

```bash
# 分析仓库，并将最后回复保存为 Markdown
codex exec -s read-only -o /tmp/codex-summary.md "概括当前仓库的目录结构"

# 同时保存过程事件和最后回复
codex exec --json -o /tmp/codex-result.md "检查文档链接并列出问题" > /tmp/codex-events.jsonl

# 允许在工作区修改文件
codex exec -s workspace-write "修正文档中的失效相对链接，并列出修改清单"

# 从文件读取任务说明
codex exec - < task.txt

# 继续当前目录最近的非交互任务
codex exec resume --last "补充刚才结果的验证方法"
```

| 参数 | 用途 |
| --- | --- |
| `-o <FILE>` | 把最后一条回复写入指定文件 |
| `--json` | 输出逐行 JSON 事件，适合脚本处理 |
| `--output-schema <FILE>` | 根据 JSON Schema 约束最终回复结构 |
| `--ephemeral` | 不持久保存本次会话记录 |
| `--skip-git-repo-check` | 允许在非 Git 目录执行 |

**旧教程兼容提醒：** `--full-auto` 已不再支持。需要编辑文件时使用 `--sandbox workspace-write`；需要自动审批时使用 `--approve-for-me`。依据[当前非交互模式说明](https://learn.chatgpt.com/docs/non-interactive-mode#permissions-and-safety)。

## 7. 代码审查

| 命令 | 审查范围 |
| --- | --- |
| `codex review --uncommitted` | 暂存、未暂存及未跟踪的改动 |
| `codex review --base main` | 相对于基准分支 `main` 的改动 |
| `codex review --commit <SHA>` | 某次提交引入的改动 |
| `codex review "重点检查错误处理和资源释放"` | 使用自定义审查要求 |

一次选择一种审查目标；自定义要求单独使用，避免与 `--base`、`--commit`、`--uncommitted` 混写。交互会话中也可以用 `/review` 选择目标。参见[官方 review 参数](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。

## 8. MCP 与插件

### MCP 服务器

| 命令 | 用途 |
| --- | --- |
| `codex mcp list` | 列出已配置服务器 |
| `codex mcp get <NAME>` | 查看指定配置；可加 `--json` |
| `codex mcp add <NAME> --url <URL>` | 添加 HTTP MCP 服务 |
| `codex mcp add <NAME> -- <COMMAND> <ARGS>` | 添加通过本地进程启动的 MCP 服务 |
| `codex mcp login <NAME>` | 为支持 OAuth 的服务登录 |
| `codex mcp logout <NAME>` | 清除该服务的 OAuth 登录凭据 |
| `codex mcp remove <NAME>` | 删除服务器配置 |

会话内用 `/mcp` 查看工具，服务器增删使用终端命令。

### 插件

| 命令 | 用途 |
| --- | --- |
| `codex plugin list` | 查看配置的及远程市场中可用的插件 |
| `codex plugin add <PLUGIN>@<MARKETPLACE>` | 从指定市场安装插件 |
| `codex plugin remove <PLUGIN>@<MARKETPLACE>` | 卸载插件并移除本地缓存 |
| `codex plugin marketplace list` | 查看插件市场 |

当前安装子命令为 `add`。插件与 MCP 的细节可分别通过 `codex plugin --help`、`codex mcp --help` 查询。

## 9. 补全与输入快捷操作

生成 Bash 补全脚本，并在当前 Bash 会话加载：

```bash
codex completion bash > /tmp/codex-completion.bash
source /tmp/codex-completion.bash
```

其他 shell 可使用 `codex completion zsh`、`codex completion fish` 或 `codex completion powershell` 生成对应脚本。

| 输入或按键 | 用途 |
| --- | --- |
| `@` | 搜索并引用工作区文件 |
| `!git status` | 在会话中运行本地 shell 命令，遵循当前权限设置 |
| `Ctrl+R` | 搜索输入历史 |
| `Ctrl+O` | 复制最近完成的回复 |
| 运行中按 `Tab` | 将输入排队到下一轮 |
| 运行中按 `Enter` | 将新指令送入当前轮次 |
| 输入框为空时连按两次 `Esc` | 编辑此前的用户消息，并从该处创建分支会话 |

快捷键可以自定义，以上为[官方默认操作说明](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。
