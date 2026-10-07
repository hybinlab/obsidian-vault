---
publish: true
tags:
  - homelab
  - 运维手册
  - Karakeep
---
> 更新：2026-10-07（从 docker-host 实际配置反推） · 位置：docker-host `192.168.31.1` `/root/karakeep/` · 重要性：**核心**
> 服务总表见 [[03-服务清单]]

## 1. 这是什么

收藏/书签管理（原 Hoarder）：收藏链接、笔记、图片、PDF，全文搜索，AI 自动打标签，有浏览器插件。

- 访问：`https://karakeep.onecloud.xin`（经 [[Caddy]]，只能在家访问）
- AI 标签：走 DeepSeek 的 OpenAI 兼容接口
- 组织方式是扁平的 lists + tags，不是文件夹树

## 2. 部署信息

官方模板的三件套：web（应用）+ chrome（抓取网页用的无头浏览器）+ meilisearch（全文搜索）。

`/root/karakeep/docker-compose.yml`：

```yaml
services:
  web:
    image: ghcr.io/karakeep-app/karakeep:${KARAKEEP_VERSION:-release}
    restart: always
    volumes:
      - data:/data
    ports:
      - 3002:3000
    env_file:
      - .env
    environment:
      MEILI_ADDR: http://meilisearch:7700
      BROWSER_WEB_URL: http://chrome:9222
      KARAKEEP_LANGUAGE: zh-CN
      DATA_DIR: /data # DON'T CHANGE THIS
  chrome:
    image: ghcr.io/karakeep-app/karakeep-chrome:release
    restart: always
    init: true
    command:
      - --disable-gpu
      - --disable-dev-shm-usage
      - --hide-scrollbars
      - --disable-blink-features=AutomationControlled
      - --window-size=1440,900
  meilisearch:
    image: getmeili/meilisearch:v1.41.0
    restart: always
    env_file:
      - .env
    environment:
      MEILI_NO_ANALYTICS: "true"
    volumes:
      - meilisearch:/meili_data
volumes:
  meilisearch:
  data:
```

`/root/karakeep/.env`：

```ini
KARAKEEP_VERSION=release
NEXTAUTH_SECRET=<占位符>
MEILI_MASTER_KEY=<占位符>
NEXTAUTH_URL=https://karakeep.onecloud.xin
OPENAI_API_KEY=<占位符>
OPENAI_BASE_URL=https://api.deepseek.com/v1
INFERENCE_TEXT_MODEL=deepseek-v4-flash
INFERENCE_IMAGE_MODEL=deepseek-v4-flash-vision-exp
INFERENCE_LANG=chinese
```

> `NEXTAUTH_URL` 必须和实际访问的域名一致，否则登录会跳错地址。

## 3. 数据

| 内容 | 位置 | 大小 | 说明 |
|---|---|---|---|
| 收藏、账号、抓取的网页快照 | 卷 `karakeep_data` | 1.5M | **不可替代** |
| 搜索索引 | 卷 `karakeep_meilisearch` | 5.9M | 可重建（后台「重建索引」） |

## 4. 日常操作

```bash
cd /root/karakeep
docker compose logs --since 1h web
docker compose pull && docker compose up -d     # 升级
```

meilisearch 是固定版本（v1.41.0），**大版本升级 meilisearch 时旧索引可能不兼容**，删掉 `karakeep_meilisearch` 卷让它重建即可。

## 5. 重建

1. 恢复 compose 和 `.env`；`NEXTAUTH_SECRET`、`MEILI_MASTER_KEY` 可以重新生成（`openssl rand -base64 36`）
2. `docker compose up -d`
3. `karakeep_data` 丢了：收藏无法找回；只丢了搜索索引：在后台重建

## 6. 已知问题与风险

- 没有备份；数据极小（1.5M），Web 端「设置 → 导出」能导出全部收藏
- `OPENAI_API_KEY` 是 DeepSeek 的付费 key，明文在 `.env` 里，注意文件权限（建议 `chmod 600 .env`）
