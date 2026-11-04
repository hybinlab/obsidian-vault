---
publish: true
tags:
  - hermes
  - Pets
  - 趣味功能
---

> 整理：2026-11-05。参考 [Hermes Pets 官方文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/pets)，并核对本机随安装提供的说明。
> 这是 Hermes 的界面宠物功能：把任务状态变成小动物的动作，还能对表达感谢、喜爱的消息作出回应。

## 有什么好玩的

宠物来自 Petdex 图库，可以在 CLI、TUI 和桌面版中显示。它跟随当前界面的任务活动切换动作：

| 当前活动 | 动画状态 |
|---|---|
| 空闲 | `idle` |
| 模型思考、阅读 | `review` |
| 执行工具、处理任务 | `run` |
| 等待澄清或审批 | `waiting`，旧素材可能退回 `idle` |
| 一轮正常完成 | `wave` |
| 计划中的待办全部完成 | `jump` |
| 工具或任务失败 | `failed` |

宠物属于显示层，不改变 Agent 的能力、提示词或工具权限。功能默认关闭，安装并选中宠物后才启用。

## Vibe reactions：说句好话，会冒爱心

给 Agent 发 `thank you`、`good bot`、`ily`、`<3` 或爱心表情，命中内置词表后会出现互动效果：桌面版浮出爱心，CLI/TUI 闪现爱心。

识别在本地进行，不为这个动画额外调用模型。它识别的是面向 Agent 的感谢和喜爱表达，而非所有积极情绪。想先确认是否正常，可用官方示例 `thank you` 或 `❤️`；其他语言、短语是否命中取决于当前版本的词表。

## 服务器上为什么不如桌面好玩

| 使用入口 | 展示情况 |
|---|---|
| 无桌面的服务器，后台运行 Gateway | 没有可承载宠物动画的交互界面 |
| 微信等消息渠道 | 现有功能不会把界面宠物同步为聊天里的动画 |
| SSH 上去交互使用 CLI/TUI | 可以尝试显示，效果取决于终端协议及连接链路 |
| 支持图形协议的终端 | 可使用像素图形渲染 |
| 普通终端 | 自动降级为真彩 Unicode 半块字符，观感更像色块 |
| 管道、重定向，无 TTY | 按设计关闭终端动画 |
| Hermes 桌面版 | 悬浮、游走、弹出窗口等交互最完整 |

SSH 本身不意味着只能看字符画，显示最终由本地终端完成。官方列出的图形终端包括 Kitty、Ghostty、WezTerm、iTerm2，也支持 sixel。中间终端层是否透传相应协议，仍需在实际使用的窗口里确认。

对当前 agent VM + 后台 Gateway + 微信的用法，Pet 主要适合偶尔 SSH 交互试玩。无需为了它给服务器安装桌面。以后使用本地桌面版时，也不能仅凭本地出现宠物，就认定它已经关联到远端 Gateway 的任务状态。

## 找一只宠物试试

先查看图库，再选择一个可用条目：

```bash
hermes pets list
hermes pets list cat

# 官方示例：安装并选中 boba
hermes pets install boba --select

# 在当前终端预览，Ctrl+C 退出
hermes pets show

# 检查安装、选中状态及渲染支持
hermes pets doctor
```

Pet 安装在当前 profile 的 `<HERMES_HOME>/pets/<slug>/` 下，不同 profile 各自管理。Hermes 使用自己的 pets 目录，不能默认认为其他工具安装到 `~/.codex/pets` 的素材会自动出现在这里。

## 常用命令

| 命令 | 用途 |
|---|---|
| `hermes pets list --installed` | 查看已安装宠物 |
| `hermes pets select <slug>` | 选中宠物 |
| `hermes pets scale 0.5` | 调整尺寸 |
| `hermes pets show --cycle` | 轮播动作 |
| `hermes pets show --state jump --once` | 播放一次庆祝动作 |
| `hermes pets show --mode unicode` | 强制字符渲染，便于比较效果 |
| `hermes pets off` | 关闭宠物 |
| `hermes pets remove <slug>` | 删除已安装宠物 |

CLI/TUI 会话内可以使用 `/pet` 切换开关、`/pet list` 选宠物、`/pet <slug>` 切换，以及 `/pet scale 0.5` 调整大小。这些是对应界面的交互命令，不应直接当成微信聊天中的通用命令。

## 桌面版玩法

从 Settings → Appearance 或 Cmd+K 的 Pets 入口管理宠物。

- **Roam**：空闲时在窗口内走动、停顿、跳跃；任务状态接管时停止游走。
- **Alt + 滚轮**：在宠物上调整尺寸。
- **Shift + 单击**：弹出为透明置顶窗口；在弹出状态再次操作可收回。
- **拖动**：移动弹出宠物的位置。
- **单击弹出宠物**：打开迷你输入框，给最近的会话发消息。
- **双击弹出宠物**：切换主窗口显示与最小化。
- **邮件图标**：离开期间任务完成后的提示，点击可回到最近线程。

弹出宠物会显示诸如 working、thinking、your turn 的气泡。它跟随桌面应用里的宠物状态，并不是额外连接 Gateway 的独立客户端。

## 配置位置与排查

设置保存在 `~/.hermes/config.yaml` 的 `display.pet` 下。优先用命令选择宠物，再按需调整；手动编辑时合并到已有 `display`，不要重复创建 YAML 键。

```yaml
display:
  pet:
    enabled: true
    slug: boba
    render_mode: auto
    scale: 0.33
    unicode_cols: 0
```

`render_mode` 可选 `auto`、`kitty`、`iterm`、`sixel`、`unicode`、`off`。强制模式不会使一个不支持该协议的终端获得图形能力。

`scale` 是整体尺寸比例；Unicode 渲染有可读性下限，无法无限缩小。`unicode_cols: 0` 表示按比例推导宽度，非零值可单独固定字符宽度。

看不到宠物时，在实际使用的终端运行 `hermes pets doctor`，核对：

1. 素材是否安装，并且已经选中、启用。
2. 当前使用的 profile 是否正确。
3. 检测到的图形协议和实际渲染模式。
4. 是否存在 TTY，以及 Pillow 能否导入。

预览动画只验证当前界面的显示能力，不代表后台任务或微信消息已经与它关联。

## 自己生成一只

Hermes 还支持 `/hatch <角色描述>`，别名 `/generate-pet`，先生成候选外观，再选择外观生成动画素材。桌面版也有对应入口。

生成自定义素材需要支持参考图的图像生成服务，会产生相应调用费用；单纯安装图库里的现成宠物不需要配置图像生成后端。想体验玩法时，先选现成宠物即可。

相关：[[配置_Hermes_Agent]]、[[安装指南 (Installation)]]。
