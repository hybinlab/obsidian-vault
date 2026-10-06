---
publish: true
tags:
  - claude-code
  - skills
  - subagents
---

> 来源：官方文档 Skills、Subagents、Features overview。返回 [[Claude Code 官方文档导读]]

## Skills

Skill 就是一个带 frontmatter 的 `SKILL.md`。它可以是**参考资料**（API 规范），也可以是**可调用的流程**（`/deploy`）。平时只有描述在上下文里，用到时才加载全文。

### 放在哪

| 位置 | 路径 | 生效范围 |
| --- | --- | --- |
| 个人 | `~/.claude/skills/<name>/SKILL.md` | 本机所有项目 |
| 项目 | `.claude/skills/<name>/SKILL.md` | 当前仓库，提交后团队共享 |
| 插件 | `<plugin>/skills/<name>/SKILL.md` | 以 `/插件名:技能名` 调用 |

旧格式 `.claude/commands/xxx.md` 仍然可用，新写的建议用 skill（可以带附属文件）。

### 示例：总结未提交改动

`~/.claude/skills/summarize-changes/SKILL.md`：

```markdown
---
description: Summarizes uncommitted changes and flags anything risky. Use when the user asks what changed, wants a commit message, or asks to review their diff.
---
## Current changes
!`git diff HEAD`

## Instructions
Summarize the changes above in two or three bullet points, then list any risks.
```

- `` !`命令` ``：**动态注入**，命令在发给 Claude 之前先执行，输出替换到这里。多行命令用 ` ```! ` 代码块。
- 调用：直接说"我改了什么？"让 Claude 自动匹配，或输入 `/summarize-changes`。

### 示例：带参数、只能手动触发的流程

```markdown
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix the GitHub issue: $ARGUMENTS.
1. Use `gh issue view` to get the issue details
2. ... implement, test, commit, open PR
```

用 `/fix-issue 1234` 调用。

### 常用 frontmatter

| 字段 | 作用 |
| --- | --- |
| `description` | 做什么、何时用。Claude 靠它判断是否自动加载，**关键场景写在最前面** |
| `disable-model-invocation: true` | 只能你手动 `/name` 触发。**有副作用的流程（部署、发消息）一定要加** |
| `user-invocable: false` | 只让 Claude 用，不出现在 `/` 菜单 |
| `allowed-tools` | 调用该技能的这一回合内免确认的工具，如 `Bash(gh *)` |
| `argument-hint` / `arguments` | 参数提示 / 命名参数 |
| `model` / `effort` | 技能执行时临时用的模型和推理强度 |
| `context: fork` + `agent` | 在子代理里运行，不污染主上下文 |
| `paths` | 只在处理匹配文件时自动加载 |

变量：`$ARGUMENTS`、`$0` `$1`…、`${CLAUDE_SKILL_DIR}`（技能目录，引用附带脚本时用）、`${CLAUDE_PROJECT_DIR}`。

### 管理

- 改了技能文件会被自动检测；新加的目录可以用 `/reload-skills` 重新扫描。
- `/skills` 列出所有技能，按 `t` 按 token 排序，按 `Space` 切换可见性。
- `/skill-doctor` 查看每个技能的上下文成本和使用频率，找出可以关掉的。

## Subagents

子代理在**独立的上下文**里运行，有自己的系统提示词和工具权限，最后只把摘要交回主会话。

### 内置子代理

| 名称 | 特点 |
| --- | --- |
| Explore | 只读、快速，专门搜索和理解代码库；不加载 CLAUDE.md |
| Plan | plan mode 下做调研用，只读 |
| general-purpose | 能读能写，处理复杂的多步任务 |

### 自定义子代理

放在 `.claude/agents/`（项目）或 `~/.claude/agents/`（个人），也可以直接让 Claude 帮你写。

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review code for:
- Injection vulnerabilities
- Authentication and authorization flaws
- Secrets or credentials in code
Provide specific line references and suggested fixes.
```

常用字段：`tools` / `disallowedTools`、`model`、`permissionMode`、`skills`（预加载的技能）、`mcpServers`、`hooks`、`memory`（子代理自己的持久记忆）、`isolation: worktree`（在独立 worktree 里改代码）、`background`。

### 调用方式

- **自然语言**："Use the security-reviewer subagent to review my changes"，由 Claude 决定是否委派；
- **@ 提及**：输入 `@` 选中子代理，保证这次一定由它执行；
- **整个会话都用它**：`claude --agent code-reviewer`，或在 settings 里写 `"agent": "code-reviewer"`。

### 什么时候用

- 要读大量文件的调研："use subagents to investigate how auth handles token refresh"；
- 实现完后**对抗式复审**：让子代理在干净的上下文里对照 PLAN.md 检查 diff，只报影响正确性或需求的问题（否则它会为了找问题而找问题）；
- 并行处理互不依赖的任务。

`/subtask <任务>` 会派生一个继承完整对话的后台子代理，做完后把结果带回当前会话。
