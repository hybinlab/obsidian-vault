# msfconsole

## 1. 简介 (Introduction)

Metasploit 是一个开源渗透测试框架，涵盖枚举、测试和攻击执行的所有阶段。

• **核心接口**: \`msfconsole\` (命令行界面)。

• **组成**: Modules (模块) 和 Tools (独立工具，如 \`msfvenom\`)。


## 2. 主要组件 (Main Components)

• **Auxiliary (辅助模块)**: 包含扫描器、爬虫和模糊测试工具。

• **Encoders (编码器)**: 混淆 Payload 以绕过基于签名的杀毒软件。

• **Evasion (规避模块)**: 尝试直接对抗杀毒软件。

• **Exploits (漏洞利用)**: 利用系统漏洞的代码。

• **NOPs**: 用于填充缓冲区 (x86 架构为 \`0x90\`)。

• **Payloads (攻击载荷)**: 在目标系统上运行的代码 (如反弹 Shell)。

• **Singles (独立)**: 包含完整功能，无需下载额外组件 (命名如 \`shell_reverse_tcp\`)

• **Stagers (分阶段)**: 建立连接并下载后续部分，体积小。

• **Stages**: 由 Stager 下载的较大 Payload。

• *命名区别*: Singles 使用 \`_\` 分隔，Staged 使用 \`/\` 分隔 (如 \`shell/reverse_tcp\`)。

• **Post (后渗透)**: 用于获取权限后的操作。


## 3. Msfconsole 常用命令

• **基本操作**: \`ls\`, \`ping\`, \`clear\`, \`help\`, \`history\`。

• **模块操作**:

• \`use \[module\]\`: 选择模块。

• \`show options\`: 显示模块参数。

• \`show payloads\`: 显示兼容的 Payload。

• \`info\`: 查看详细信息。

• \`search \[keyword\]\`: 搜索模块 (支持 CVE、名称等)。

• \`back\`: 返回上一级。


## 4. 模块使用与参数 (Working with Modules)

• **设置参数**: \`set PARAMETER_NAME VALUE\`

• **关键参数**:

• **RHOSTS**: 目标 IP 或网段 (支持 CIDR 或文件列表 \`file:/path/list.txt\`)。

• **RPORT**: 目标端口。

• **LHOST**: 攻击机 (本地) IP。

• **LPORT**: 本地监听端口。

• **SESSION**: 指定会话 ID。

• **全局设置**: \`setg\` (全局设置)，\`unsetg\` (清除全局)。

• **执行**: \`exploit\` 或 \`run\`。

 • \`exploit -z\`: 运行并立即后台化。

• \`check\`: 检查漏洞是否存在 (不攻击)。

\n

## 5. 会话管理 (Sessions)

• **后台化**: 输入 \`background\` 或按 \`CTRL+Z\`。

• **查看会话**: \`sessions\`。

• **进入会话**: \`sessions -i \[ID\]\`。