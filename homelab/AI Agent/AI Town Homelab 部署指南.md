---
publish: true
---
# AI Town Homelab 部署指南

> 适用环境：Docker 宿主机（Linux），自有 LLM 供应商（OpenAI 兼容接口）


---

## 前置要求

* Docker + Docker Compose
* Node.js（用于运行 `npx convex` CLI）
* 可访问的 OpenAI 兼容 LLM 接口（含 embedding 模型）


---

## 部署步骤

### 1. 克隆项目并安装依赖

```bash
git clone https://github.com/a16z-infra/ai-town.git
cd ai-town
npm install
```

> ⚠️ 必须先运行 `npm install`，否则后续 `npx convex deploy` 会报 `Could not resolve "convex/server"` 错误。


---

### 2. 修改 docker-compose.yml

`docker-compose.yml` 默认将后端地址硬编码为 `127.0.0.1`，从局域网其他机器访问时前端 WebSocket 会连接失败。需将宿主机局域网 IP 替换进去：

```yaml
services:
  frontend:
    environment:
      - VITE_CONVEX_URL=http://<宿主机IP>:${PORT:-3210}   # 改这里

  backend:
    environment:
      - CONVEX_CLOUD_ORIGIN=http://<宿主机IP>:${PORT:-3210}    # 改这里
      - CONVEX_SITE_ORIGIN=http://<宿主机IP>:${SITE_PROXY_PORT:-3211}  # 改这里
```

或者在项目根目录创建 `.env` 文件统一管理（`VITE_CONVEX_URL` 那行因为硬编码，必须直接改 `docker-compose.yml`）：

```env
URL_BASE=http://<宿主机IP>
```


---

### 3. 启动容器

```bash
docker compose up -d
```

启动后服务端口：

| 服务 | 地址 |
|----|----|
| 游戏前端 | `http://<宿主机IP>:5173` |
| Convex 后端 | `http://<宿主机IP>:3210` |
| Convex 控制台 | `http://<宿主机IP>:6791` |


---

### 4. 生成 Admin Key 并写入配置

```bash
docker compose exec backend ./generate_admin_key.sh
```

将输出的 key 写入项目根目录的 `.env.local`：

```env
CONVEX_SELF_HOSTED_ADMIN_KEY="convex-self-hosted|xxxxxxxx"
CONVEX_SELF_HOSTED_URL="http://127.0.0.1:3210"
```

> ⚠️ `CONVEX_SELF_HOSTED_URL` 这里保持 `127.0.0.1`，这是 CLI 在宿主机本地连后端用的，不影响前端。
>
> ⚠️ 每次执行 `docker compose down` 再 `up`，Admin Key 会失效，需重新生成并更新 `.env.local`。


---

### 5. 修改 Embedding 维度

根据你使用的 embedding 模型，修改 `convex/util/llm.ts` 中的 `EMBEDDING_DIMENSION`：

| 模型 | 维度 |
|----|----|
| `bge-m3` / `BAAI/bge-m3` | `1024` |
| `Qwen3-Embedding-8B` | `4096` |
| `bge-multilingual-gemma2` | `3584` |

```typescript
// convex/util/llm.ts 顶部
const EMBEDDING_DIMENSION = 1024;  // 按你的模型修改
```

> ⚠️ 维度填错会导致向量数据库报错，切换模型后需要重置数据库。


---

### 6. 部署 Convex 函数

```bash
npx convex deploy
```

成功后输出类似：

```
✔ Schema validation complete.
✔ Deployed Convex functions to http://127.0.0.1:3210
```


---

### 7. 配置 LLM 供应商

使用任意 OpenAI 兼容接口：

```bash
npx convex env set LLM_API_URL 'https://your-api-endpoint/v1'
npx convex env set LLM_API_KEY 'your-api-key'
npx convex env set LLM_MODEL 'your-chat-model-name'
npx convex env set LLM_EMBEDDING_MODEL 'bge-m3'
```


---

### 8. 初始化世界

```bash
npx convex run init
```


---

### 9. 访问

浏览器打开 `http://<宿主机IP>:5173`，看到角色在地图上走动即部署成功。


---

## 常见问题

| 现象 | 原因 | 解决 |
|----|----|----|
| WebSocket 连接 `127.0.0.1:3210` 失败 | `docker-compose.yml` 中地址未改为宿主机 IP | 修改 `VITE_CONVEX_URL` 和 `CONVEX_CLOUD_ORIGIN` |
| `Could not find public function for 'world:defaultWorldStatus'` | Convex 函数未部署 | 运行 `npx convex deploy` |
| `Could not resolve "convex/server"` | node_modules 未安装 | 运行 `npm install` |
| `No CONVEX_DEPLOYMENT set` | `.env.local` 未配置或路径错误 | 检查项目根目录下的 `.env.local` |
| 切换 embedding 模型后报向量维度错误 | `EMBEDDING_DIMENSION` 与模型不匹配 | 修改 `convex/util/llm.ts` 并重置数据库 |