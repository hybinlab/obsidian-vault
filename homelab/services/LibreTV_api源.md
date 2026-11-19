---
tags:
  - homelab
  - 运维手册
  - LibreTV
---
> 更新：2026-11-19 · 服务：LibreTV v2.24.0 · 内容：视频源订阅配置 · 验证状态：订阅成功

## 1. 文档信息

| 项目 | 说明 |
|---|---|
| 配置方式 | GitHub Gist + JSON 远程订阅 |
| 配置类型 | 点播源 / 直播源 |
| 适用场景 | Docker 自部署或其他支持数据源订阅的 LibreTV 实例 |

## 2. 方案概述

LibreTV 支持通过远程 URL 订阅视频源配置。

本方案使用 GitHub Gist 托管 JSON 配置文件，再通过 LibreTV 的数据源订阅功能加载。

**数据流**：

```text
视频源 JSON 配置
       │
       ▼
  GitHub Gist
       │
       ▼
  Raw HTTPS URL
       │
       ▼
 LibreTV 数据源订阅
       │
       ▼
   加载视频源
```

**方案优势**：

- 无需额外部署 HTTP 文件服务器。
- 无需购买域名或配置反向代理。
- 使用 HTTPS 访问配置文件。
- 可通过 GitHub Gist 修改和维护配置。
- 可在多个 LibreTV 实例之间复用订阅地址。

> 注意：Gist 仅负责托管配置文件，不保证第三方视频接口的可用性。

## 3. 前置条件

1. LibreTV 实例正常运行。
2. LibreTV 版本支持数据源订阅功能。
3. 拥有 GitHub 账号。
4. 已准备符合 LibreTV 要求的 JSON 配置文件。
5. LibreTV 所在环境能够访问 Gist Raw 地址。

参考项目：

- [LibreTV 项目仓库](https://github.com/LibreSpark/LibreTV)
- [社区视频源讨论](https://github.com/LibreSpark/LibreTV/discussions/652)
- [GitHub Gist](https://gist.github.com/)

## 4. 操作步骤

### 4.1 准备 JSON 配置

准备视频源配置文件 `LibreTV-SourceList.json`。

配置文件应采用 LibreTV 当前版本支持的 JSON 结构。

建议在发布前完成以下检查：

- JSON 语法合法。
- 视频源名称与接口地址完整。
- 删除重复接口。
- 区分点播源与直播源。
- 避免包含账号密码、Token 等敏感信息。

可以使用 Python 验证 JSON 语法：

```bash
python3 -m json.tool LibreTV-SourceList.json > /dev/null
```

命令退出码为 `0` 表示 JSON 语法有效。

> JSON 语法有效不代表配置结构一定符合 LibreTV 的要求。

### 4.2 创建 GitHub Gist

访问 [GitHub Gist](https://gist.github.com/)。

操作流程：

1. 登录 GitHub。
2. 创建新的 Gist。
3. 文件名填写 `LibreTV-SourceList.json`。
4. 粘贴完整 JSON 内容。
5. 选择 **Create public gist**。
6. 保存创建后的 Gist 页面地址。

### 4.3 获取 Raw 地址

进入刚刚创建的 Gist。

找到 JSON 文件，点击 **Raw**。

Raw 地址通常采用以下格式：

```text
https://gist.githubusercontent.com/<username>/<gist-id>/raw/LibreTV-SourceList.json
```

实际地址可能包含版本修订标识，应以 GitHub 提供的地址为准。

**Gist 页面地址**：

```text
https://gist.github.com/<username>/<gist-id>
```

**JSON 原始文件地址**：

```text
https://gist.githubusercontent.com/<username>/<gist-id>/raw/LibreTV-SourceList.json
```

LibreTV 应使用后者。

### 4.4 验证订阅地址

首先通过浏览器访问 Raw URL。

正常情况下应直接返回 JSON 内容。

也可以使用命令行检查：

```bash
curl -L -I "<RAW_URL>"
```

预期结果：

```text
HTTP/2 200
```

进一步验证返回内容：

```bash
curl -fLsS "<RAW_URL>" \
  | python3 -m json.tool > /dev/null
```

如果命令成功退出，说明当前地址返回了语法合法的 JSON。

### 4.5 LibreTV 添加订阅

进入 LibreTV Web UI。

依次打开：

```text
设置
 └── 源管理
      └── 数据源订阅
```

操作流程：

1. 找到「数据源订阅 / 分享」。
2. 在订阅地址输入框中粘贴 Raw URL。
3. 点击「订阅」。
4. 等待 LibreTV 处理配置。
5. 检查点播源、直播源是否成功加载。

**验收标准**：

- 未出现 HTTP 错误。
- 未出现 JSON 解析错误。
- 视频源能够正常显示。
- 能够使用已配置的视频源进行搜索。

> 订阅成功仅代表配置加载成功，实际播放能力仍需单独验证。

## 5. 故障排查

### 5.1 HTTP 404

**现象**：

```text
订阅地址返回 HTTP 404
```

**可能原因**：

- 使用了错误的 Gist URL。
- Raw 地址复制不完整。
- Gist 文件已删除。
- 文件名或修订路径错误。

**处理方法**：

1. 打开 Gist 页面。
2. 确认 JSON 文件存在。
3. 重新点击 Raw。
4. 复制完整地址。
5. 在浏览器中验证。
6. 返回 LibreTV 重新订阅。

### 5.2 HTTP 403

**可能原因**：

- 请求被网络策略限制。
- GitHub 访问受到代理或防火墙影响。
- 请求触发服务端访问限制。

**处理方法**：

```bash
curl -IL "<RAW_URL>"
```

检查实际 HTTP 状态码及重定向结果。

如果 LibreTV 部署在 Docker 中，还需要确认容器网络能够访问目标地址。

### 5.3 JSON 解析失败

**可能原因**：

- JSON 格式错误。
- 存在多余逗号。
- 字符串未正确转义。
- 配置结构不符合 LibreTV 要求。

**处理方法**：

```bash
python3 -m json.tool LibreTV-SourceList.json
```

如果语法检查通过，但 LibreTV 仍无法解析，应进一步检查配置字段及数据结构。

### 5.4 订阅成功但无法播放

**可能原因**：

- 第三方视频接口失效。
- 视频资源已下线。
- 接口响应异常。
- 播放地址存在跨域或网络限制。

**处理方法**：

1. 检查视频源接口是否可访问。
2. 使用 LibreTV 提供的测活功能（如当前版本支持）。
3. 测试具体视频资源。
4. 删除长期不可用的视频源。

## 6. 日常维护

### 6.1 更新视频源

当需要新增、删除或修改视频源时：

1. 打开原 GitHub Gist。
2. 点击 Edit。
3. 修改 JSON 内容。
4. 保存更新。
5. 在 LibreTV 中重新加载订阅。

注意：如果原订阅 URL 包含固定的 Gist 修订版本标识，更新文件后可能仍然获取旧内容。

建议使用不固定修订版本的 Raw URL，并在更新后验证返回内容。

### 6.2 维护建议

| 维护项目 | 建议 |
|---|---|
| 视频源可用性 | 定期检查 |
| 失效接口 | 及时移除 |
| 重复接口 | 合并去重 |
| JSON 配置 | 保留历史版本 |
| Gist 地址 | 使用稳定的 Raw URL |
| 配置安全 | 不存储敏感凭据 |

## 7. 安全注意事项

1. Public Gist 内容对外公开，不得存放敏感信息。
2. 第三方视频接口可能收集访问请求及相关网络信息。
3. 视频源的可访问性不代表其内容具有合法授权。
4. 不建议直接导入来源不明、未经检查的配置。
5. 修改配置前应保留可恢复的历史版本。

## 8. 最终验收

| 检查项 | 预期结果 |
|---|---|
| Gist 文件可访问 | HTTP 200 |
| Raw URL 返回内容 | 合法 JSON |
| LibreTV 订阅 | 成功 |
| 视频源加载 | 正常 |
| 视频搜索 | 正常 |
| 视频播放 | 至少一个授权测试源播放成功 |

**最终状态**：LibreTV v2.24.0 已通过 GitHub Gist Raw URL 完成数据源订阅配置。

后续维护只需更新 Gist 中的 JSON 文件，并根据需要在 LibreTV 中重新加载订阅。
