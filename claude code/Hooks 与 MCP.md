---
publish: true
tags:
  - claude-code
  - hooks
  - mcp
---

> 来源：官方文档 Hooks guide、MCP。返回 [[Claude Code 官方文档导读]]

## Hooks

Hook 是在 Claude Code 生命周期的特定事件上**一定会执行**的动作。和 CLAUDE.md 里的指令不同，它是确定性的：**护栏、必须每次都做的事，用 hook**。

### 常用事件

| 事件 | 触发时机 |
| --- | --- |
| `SessionStart` / `SessionEnd` | 会话开始（含恢复）/ 结束 |
| `UserPromptSubmit` | 提交提示词后、Claude 处理前 |
| `PreToolUse` | 工具调用前，**可以拦截** |
| `PostToolUse` | 工具调用成功后（比如编辑后跑格式化） |
| `PermissionRequest` | 需要权限决定时 |
| `Notification` | Claude 等待输入或权限时 |
| `Stop` | Claude 回复结束时（可以拦住，让它继续干直到检查通过） |
| `SubagentStart` / `SubagentStop` | 子代理启动 / 结束 |
| `PreCompact` / `PostCompact` | 压缩上下文前后 |
| `CwdChanged` / `FileChanged` | 目录或被监视的文件变化 |

完整列表见官方 hooks 参考。Hook 类型除了 `command`（shell 命令），还有 `http`、`mcp_tool`、`prompt`（单轮 LLM 判断）、`agent`（实验性）。

### 输入输出约定

- 事件数据以 JSON 形式通过 **stdin** 传给脚本；
- **exit 0**：不表态，走正常流程（`SessionStart`、`UserPromptSubmit` 的 stdout 会加入上下文）；
- **exit 2**：**拦截**，写到 stderr 的原因会反馈给 Claude；
- 其他退出码：看 stdout 输出的 JSON 决定。

### 例 1：需要输入时发桌面通知（Linux）

`~/.claude/settings.json`：

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "notify-send 'Claude Code' 'Claude Code needs your attention'" }
        ]
      }
    ]
  }
}
```

> 服务器上没有桌面环境的话，可以把 command 换成 curl 推送到 ntfy 之类的服务。

### 例 2：禁止修改敏感文件

`.claude/hooks/protect-files.sh`（记得 `chmod +x`）：

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")
for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done
exit 0
```

`.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh" }
        ]
      }
    ]
  }
}
```

### 小技巧

- `matcher` 按工具名过滤，支持 `Edit|Write` 这种写法；
- 不想手写的话，直接让 Claude 写："Write a hook that runs eslint after every file edit"；
- `/hooks` 查看当前生效的所有 hook；
- 所有来源的 hook 会**合并**执行，不会互相覆盖。

## MCP

MCP 让 Claude 连接外部服务（数据库、Notion、Sentry、浏览器……）。工具 schema 按需加载，闲置时几乎不占上下文。

### 添加服务器

```bash
# 远程 HTTP（推荐）
claude mcp add --transport http notion https://mcp.notion.com/mcp

# 本地 stdio：-- 之后的部分原样作为启动命令
claude mcp add --env API_KEY=<你的key> db -- npx -y @bytebase/dbhub

# 直接给 JSON
claude mcp add-json weather '{"type":"http","url":"https://example.com/mcp"}'

# 管理
claude mcp list
claude mcp get notion
claude mcp remove notion
claude mcp login sentry      # OAuth 认证
```

会话内用 `/mcp` 查看连接状态、认证、启用或禁用。

### 作用域

| scope | 生效范围 | 存放位置 |
| --- | --- | --- |
| `local`（默认） | 当前项目，仅自己 | `~/.claude.json` |
| `project` | 当前项目，团队共享 | 项目根目录的 `.mcp.json` |
| `user` | 自己的所有项目 | `~/.claude.json` |

用 `--scope user` 等参数指定。同名时优先级为 local > project > user。

`.mcp.json` 支持环境变量展开，**密钥不要直接写进去**：

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": { "Authorization": "Bearer ${API_KEY}" }
    }
  }
}
```

### 经验

- 能用 CLI 的优先用 CLI（`gh`、`aws`、`kubectl`），这是最省上下文的方式；Claude 也能通过 `xxx --help` 学会新工具。
- MCP 提供连接，Skill 教 Claude 怎么用好它，两者经常一起用：比如 MCP 连数据库，Skill 写表结构和查询规范。
