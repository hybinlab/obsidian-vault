---
publish: true
tags:
  - claude-code
  - 记忆
---

> 来源：官方文档 Memory、Best practices。返回 [[Claude Code 官方文档导读]]

Claude Code 有两套记忆，都在会话开始时加载，但都只是**上下文，不是强制配置**。要强制禁止某个行为，用 PreToolUse hook（见 [[Hooks 与 MCP]]）。

| | CLAUDE.md | Auto memory |
| --- | --- | --- |
| 谁写 | 你 | Claude 自己 |
| 内容 | 指令和规则 | 学到的偏好、你的纠正、项目背景 |
| 范围 | 组织 / 用户 / 项目 | 每个仓库一份（所有 worktree 共享） |
| 加载 | 全文 | `MEMORY.md` 前 200 行或 25KB |

## CLAUDE.md 放在哪

按加载顺序（越往下越具体、越后读到）：

| 范围 | 位置 | 用途 |
| --- | --- | --- |
| 组织策略 | Linux：`/etc/claude-code/CLAUDE.md` | 公司统一规范 |
| 用户 | `~/.claude/CLAUDE.md` | 个人偏好，对所有项目生效 |
| 项目 | `./CLAUDE.md` 或 `./.claude/CLAUDE.md` | 团队共享，提交到 git |
| 本地 | `./CLAUDE.local.md` | 个人的项目偏好，加入 `.gitignore` |

- 启动目录**及所有上级目录**里的 CLAUDE.md 都会加载，内容是**拼接**而不是覆盖。
- 子目录里的 CLAUDE.md 在 Claude 读写那个子目录的文件时才加载。
- 块级 HTML 注释 `<!-- ... -->` 会在注入前去掉，可以用来给人类维护者留言，不占 token。
- `/init` 自动生成初版；`/context` 确认是否加载；`/memory` 打开编辑。

## 怎么写才有效

- **控制在 200 行以内**。每一行都问自己："删掉它 Claude 会犯错吗？" 不会就删。太长会导致重要规则被忽略。
- 写**可验证**的具体指令：
  - ✅ "Use 2-space indentation" ❌ "Format code properly"
  - ✅ "Run `npm test` before committing" ❌ "Test your changes"
- 某条总被忽略，可以单独加 "IMPORTANT"；但到处强调等于没强调。
- 定期用 `/doctor prompt-audit` 检查过时或矛盾的指令。

| ✅ 应该写 | ❌ 不要写 |
| --- | --- |
| Claude 猜不到的 Bash 命令 | 读代码就能知道的东西 |
| 与默认不同的代码风格 | 语言的通用惯例 |
| 测试方式和首选测试工具 | 详细 API 文档（给链接即可） |
| 仓库规矩（分支命名、PR 约定） | 经常变化的信息 |
| 项目特有的架构决策 | 长篇解释、教程 |
| 开发环境的坑（必需的环境变量） | 逐个文件的说明 |

**什么时候往里加**：Claude 第二次犯同样的错；code review 发现它本该知道的事；你在聊天里重复上次说过的纠正。

## 导入其他文件

```text
See @README for project overview and @package.json for npm commands.
- git workflow @docs/git-instructions.md
- @~/.claude/my-project-instructions.md
```

- 相对路径相对于**写导入的那个文件**；最多递归 4 层。
- 路径有空格时用 `\ ` 转义；写在反引号里的 `@xxx` 不会被导入。
- 导入不省 token：被导入的文件同样在启动时全部加载。
- 项目文件导入工作目录以外的文件时，第一次会弹窗确认。

## `.claude/rules/`：拆分规则

```text
.claude/
├── CLAUDE.md
└── rules/
    ├── code-style.md
    ├── testing.md
    └── security.md
```

- 没有 `paths` 的规则文件每次都加载；
- 带 `paths` frontmatter 的规则**只在 Claude 读写匹配文件时**才加载，省上下文：

```markdown
---
paths:
  - "src/api/**/*.ts"
---
- All API endpoints must include input validation
```

## Auto memory

- 默认开启。Claude 会自己记四类笔记：`user`（你的角色和偏好）、`feedback`（你的纠正）、`project`（进行中的工作和决策）、`reference`（外部资源的位置）。
- 存放位置：`~/.claude/projects/<project>/memory/`，`MEMORY.md` 是索引（每次加载），具体内容放在各个主题文件里按需读取。
- 只存在本机，不跨机器同步。
- 说"记住：总是用 pnpm"→ 存进 auto memory；说"把这条加到 CLAUDE.md"→ 写进 CLAUDE.md。
- 开关：`/memory` 里切换，或设 `"autoMemoryEnabled": false`，或设环境变量 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`。
- 都是普通 markdown，可以随时手动编辑或删除。

## AGENTS.md

如果仓库用的是 `AGENTS.md`（其他编程工具的约定），Claude Code 也能读取；`/import codex|gemini|cursor` 可以把其他工具的配置迁移过来。
