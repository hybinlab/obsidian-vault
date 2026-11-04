---
publish: true
tags:
  - hermes
  - Lightpanda
  - 浏览器自动化
---

> 整理：2026-11-05。基于本机安装结果、`lightpanda help` 及 Hermes 随安装提供的浏览器文档。
> Lightpanda 可以由 Hermes 管理，也可以作为独立命令由人或具备终端权限的 Agent 调用。

## 本机安装记录

| 项目 | 信息 |
|---|---|
| 所在主机 | agent VM，Ubuntu 24.04，x86_64，4C/8G |
| 可执行文件 | `/root/.local/bin/lightpanda` |
| 本次核对版本 | `1.1.0-nightly.11647+b8e234a77` |
| 安装确认 | 用户已完成安装，`--help` 与 `version` 可运行 |
| Hermes 接入 | 本机 Hermes 已包含 Lightpanda 本地引擎支持 |

版本是 nightly，更新后应重新核对命令参数与常用网站兼容性。安装方式参考 [Lightpanda 官方安装指南](https://lightpanda.io/docs/run-locally/installation/one-liner)；项目及发行包见 [官方仓库](https://github.com/lightpanda-io/browser)。

```bash
export PATH="/root/.local/bin:$PATH"
lightpanda version
lightpanda --help
```

需要在后续交互式终端中持续生效时，将 PATH 设置放入对应 shell 的启动文件，再重新加载。服务进程的 PATH 由服务配置决定，不会因为当前终端执行了 `source ~/.bashrc` 自动改变。调用脚本时也可以直接使用绝对路径。

## 什么时候用

Lightpanda 是面向自动化的无头浏览器，具备 JavaScript、DOM 和浏览器控制能力。适合动态页面读取、结构化内容提取及程序化页面交互。

| 需求 | 使用方式 |
|---|---|
| 读取网页，保存为 Markdown/HTML | `fetch` |
| 等待 JavaScript 生成内容 | `fetch` 的等待条件，或浏览器控制客户端 |
| 连续点击、填写表单、读取 DOM | Hermes 浏览器工具，或连接 CDP 的客户端 |
| 重复运行已有自动化脚本 | `run` |
| 作为其他 Agent 的浏览器工具 | 终端直接调用，或配置 MCP |

无需浏览器交互的简单网页读取，仍可用 HTTP 请求或网页提取工具。遇到需要真实视觉布局、复杂登录挑战等页面，应根据实际兼容性选择其他浏览器。

## 接入 Hermes

安装完成后，在 `~/.hermes/config.yaml` 已有的 `browser` 配置块中合并以下设置，不要重复创建同名 YAML 键：

```yaml
browser:
  cloud_provider: local
  engine: lightpanda
  inactivity_timeout: 120
```

也可以通过 `hermes tools` 的浏览器选项选择 Lightpanda。环境变量 `AGENT_BROWSER_ENGINE=lightpanda` 是另一种选择方式，具体优先级以当前 Hermes 版本为准。

Hermes 的 Browser Use 模式会按需启动本地 Lightpanda，使用回环地址和空闲端口，再由浏览器驱动连接；空闲回收和进程清理由 Hermes 管理。按这种方式接入时，不需要另外手动启动一个固定端口的常驻 `serve` 服务。

如果配置后仍使用其他浏览器，检查是否存在云浏览器、显式 CDP 地址、Camofox 或真实浏览器 profile 等更高优先级设置。浏览器引擎在部分 Hermes 代码路径中有进程内缓存，已经运行的 Gateway 是否需要重载，应按实际版本和使用方式确认；不能直接套用 Webhook 动态路由的热加载规则。

安装二进制、选择引擎和授予浏览器工具权限是三个不同环节。选择引擎不会自动为受限的告警诊断路由增加浏览器或终端权限。

Hermes 的集成说明见 [官方 Browser 文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser#lightpanda-local-engine)。

## 从终端直接读取网页

独立调用不需要先经过 Hermes。具备终端执行权限的其他本机 Agent，也可以运行相同命令。

### 读取 Markdown

```bash
/root/.local/bin/lightpanda fetch https://example.com \
  --dump markdown \
  --dump-max-bytes 50000 \
  --wait-ms 10000 \
  --terminate-ms 15000 \
  --fail-on-http-error
```

`--wait-ms` 控制等待预算，`--terminate-ms` 提供页面执行的硬截止时间。`--fail-on-http-error` 使 HTTP 4xx/5xx 返回失败退出码，便于脚本判断。

保存临时结果：

```bash
lightpanda fetch https://example.com \
  --dump markdown --dump-max-bytes 50000 \
  --terminate-ms 15000 --fail-on-http-error \
  > /tmp/lightpanda-example.md
```

`/tmp` 中的提取结果是临时文件；需要长期保存的内容，应整理成笔记后按主题存入知识库。

### 等待页面元素，再读取 HTML

```bash
lightpanda fetch https://example.com \
  --wait-selector h1 \
  --dump html --dump-max-bytes 50000 \
  --wait-ms 10000 --terminate-ms 15000 \
  --fail-on-http-error
```

实际使用时替换 URL 和 selector。也支持 `--wait-script` 等待 JavaScript 表达式满足条件；具体语法查看 `lightpanda help fetch`。

### 获取便于脚本处理的结果

```bash
lightpanda fetch https://example.com \
  --dump markdown --json \
  --dump-max-bytes 50000 --terminate-ms 15000 \
  --fail-on-http-error
```

同时检查退出码、HTTP 状态及 JSON 中的 `error`，不要仅凭 stdout 有内容就认定页面成功读取。多 URL 抓取需要 `--json`。

## CDP 与 MCP

这两种方式用于外部客户端集成，按实际需求选择，不必都开启。

```bash
# 手动提供 CDP 服务，供 Puppeteer、Playwright 等兼容客户端连接
lightpanda serve --host 127.0.0.1 --port 9222

# MCP stdio 模式，由调用方管理进程
lightpanda mcp

# MCP HTTP 模式
lightpanda mcp --host 127.0.0.1 --port 9223
```

CDP 示例连接地址是 `ws://127.0.0.1:9222`；MCP HTTP 地址是 `http://127.0.0.1:9223/mcp`，两种协议不能混用。

MCP 客户端配置形式：

```json
{
  "mcpServers": {
    "lightpanda": {
      "command": "/root/.local/bin/lightpanda",
      "args": ["mcp"]
    }
  }
}
```

字段层级取决于使用的客户端；上例表达的是启动命令及参数，并不是所有 Agent 的通用配置文件。MCP HTTP 模式支持按会话标识隔离浏览状态，具体生命周期见 `lightpanda help mcp`。

## 功能边界与验证

- 本机 CLI 支持 HTML、Markdown、结构化数据，以及文本型 PNG/PDF 导出。文本型渲染不等于完整网页视觉截图。
- 本机 Hermes 集成文档仍将 Lightpanda 描述为文本优先、单页面模式，`capture_screenshot()` 不可用；以实际驱动支持为准。
- 同一 Hermes Lightpanda 浏览器会话中，按当前驱动约定首次使用 `new_tab()`，后续导航使用 `goto_url()`。不要假定所有 Chromium CDP 方法都受支持。
- 普通 `fetch` 与已有脚本的 `run` 不需要额外启动一个 LLM；`lightpanda agent` 是另一个会使用模型的模式，不能混为一谈。
- 动态网页、登录流程和反自动化限制需要用实际目标站点验证，官方性能基准不能直接当成本机资源占用保证。

可分三步确认是否真正可用：二进制能运行；目标页面能加载并提取到预期内容；实际使用方（Hermes、脚本或 MCP 客户端）能调用成功。仅 `--help` 成功只能确认第一步。

常用帮助：

```bash
lightpanda help fetch
lightpanda help serve
lightpanda help mcp
lightpanda help run
```

相关：[[配置_Hermes_Agent]]、[[Webhooks（事件触发与消息投递）]]。
