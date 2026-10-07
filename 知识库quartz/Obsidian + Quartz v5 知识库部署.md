> 从零开始，将 Obsidian 笔记通过 Quartz v5 发布到 GitHub Pages 的完整可复现流程。

## 架构概览

```
私有仓库 obsidian-vault (存放全部笔记)
    │
    │  Obsidian Git 插件自动 commit/push
    │
    ▼  push 触发 repository_dispatch
公开仓库 quartz-site (Quartz v5)
    │
    │  GitHub Actions:
    │    1. checkout 自身
    │    2. checkout vault → content/ (deploy key)
    │    3. rm -rf 私密目录
    │    4. npm i && npx quartz build
    │    5. deploy to GitHub Pages
    │
    ▼
https://<username>.github.io/quartz-site/
```

## 前置条件

- GitHub 账号，安装 `gh` CLI 并登录（`gh auth login`）
- Mac/Linux 终端环境
- 本地已有 Obsidian vault
- Node.js 22+

---

## 第一步：创建私有 vault 仓库

### 1.1 初始化 vault 的 Git 仓库

```bash
cd ~/path/to/your-vault

# 创建 .gitignore
cat > .gitignore << 'EOF'
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.trash/
.DS_Store
EOF

git init
git add .
git commit -m "init: obsidian vault"
```

### 1.2 在 GitHub 创建私有仓库并推送

```bash
gh repo create obsidian-vault --private --source=. --push
```

> **注意**：如果在中国大陆，SSH 可能被墙（端口 22 被阻断）。改用 HTTPS：
> 
> ```bash
> git remote set-url origin https://github.com/<username>/obsidian-vault.git
> ```
> 
> 或者配置 SSH 走 443 端口，在 `~/.ssh/config` 添加：
> 
> ```
> Host github.com
>     Hostname ssh.github.com
>     Port 443
>     User git
> ```

### 1.3 创建首页 index.md

在 vault 根目录创建 `index.md`，作为站点首页：

```markdown
---
title: 你的知识库名称
---

欢迎来到知识库。
```

提交并推送：

```bash
git add index.md
git commit -m "add homepage"
git push origin main
```

---

## 第二步：创建 Quartz 站点仓库

### 2.1 Fork 或 clone Quartz v5

```bash
# 方式一：直接 clone（推荐，避免 fork 关系干扰）
gh repo create quartz-site --public
git clone https://github.com/<username>/quartz-site.git
cd quartz-site

# 拉取 Quartz v5 代码
git remote add upstream https://github.com/jackyzha0/quartz.git
git fetch upstream v5
git checkout -b v5 upstream/v5
git push -u origin v5
```

> 确认默认分支是 `v5`（在 GitHub 仓库 Settings → General → Default branch 修改）。

### 2.2 清理多余的 workflow 文件

Quartz 上游可能自带多个 workflow 文件，只保留我们自己的：

```bash
# 查看现有 workflow
ls .github/workflows/

# 删除所有上游自带的（通常是 .yaml 后缀）
rm -f .github/workflows/*.yaml

# 后面我们会创建自己的 deploy.yml
```

### 2.3 修改 Quartz 配置

编辑 `quartz.config.default.yaml`：

```yaml
configuration:
  pageTitle: 你的知识库名称
  pageTitleSuffix: ""
  enableSPA: true
  enablePopovers: true
  analytics:
    provider: plausible
  locale: zh-CN
  baseUrl: <username>.github.io/quartz-site
  ignorePatterns:
    - private
    - templates
    - .obsidian
    # 按需添加不想公开的文件夹，如：
    # - 随笔/日记
```

关键改动：

- `pageTitle`：站点标题
- `locale`：`zh-CN`
- `baseUrl`：`<username>.github.io/quartz-site`（不带 `https://`，不带尾部 `/`）
- `ignorePatterns`：不想发布的文件夹

---

## 第三步：配置跨仓库访问（Deploy Key）

### 3.1 生成 SSH 密钥对

```bash
ssh-keygen -t ed25519 -C "quartz-deploy" -f /tmp/quartz-deploy-key -N ""
```

### 3.2 将公钥添加到 vault 仓库

```bash
gh repo deploy-key add /tmp/quartz-deploy-key.pub \
  -R <username>/obsidian-vault \
  --title "quartz-site-read"
```

### 3.3 将私钥添加到 quartz-site 的 Secrets

```bash
gh secret set VAULT_DEPLOY_KEY \
  -R <username>/quartz-site \
  < /tmp/quartz-deploy-key
```

### 3.4 清理密钥文件

```bash
rm /tmp/quartz-deploy-key /tmp/quartz-deploy-key.pub
```

---

## 第四步：创建 GitHub Actions 部署工作流

### 4.1 创建 deploy.yml

在 quartz-site 仓库中：

```bash
mkdir -p .github/workflows
cat > .github/workflows/deploy.yml << 'DEPLOY_EOF'
name: Build and Deploy
on:
  workflow_dispatch:
  push:
    branches: [v5]
  repository_dispatch:
    types: [vault-updated]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Checkout vault
        uses: actions/checkout@v4
        with:
          repository: <username>/obsidian-vault
          ssh-key: ${{ secrets.VAULT_DEPLOY_KEY }}
          path: content

      - name: Filter private content
        run: |
          rm -rf content/.obsidian content/.trash content/.git

      - uses: actions/setup-node@v4
        with:
          node-version: 22

      - run: npm i
      - run: npx quartz build

      - uses: actions/upload-pages-artifact@v3
        with:
          path: public

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
DEPLOY_EOF
```

> **重要**：将 `<username>` 替换为你的 GitHub 用户名。

### 4.2 提交并推送

```bash
git add .
git commit -m "feat: quartz site with vault integration"
git push origin v5
```

---

## 第五步：配置 GitHub Pages

### 5.1 设置 Pages 来源

在浏览器中打开：`https://github.com/<username>/quartz-site/settings/pages`

将 **Source** 改为 **GitHub Actions**（不是 "Deploy from a branch"）。

> 此步**必须手动操作**，API 设置会返回 422 错误。

### 5.2 验证首次部署

```bash
# 查看 workflow 运行状态
gh run list -R <username>/quartz-site --workflow=deploy.yml --limit 1

# 等待运行完成
gh run watch <run-id> -R <username>/quartz-site
```

部署完成后访问 `https://<username>.github.io/quartz-site/` 验证。

---

## 第六步：配置 Vault 自动触发构建

### 6.1 创建 PAT (Personal Access Token)

在浏览器打开：`https://github.com/settings/tokens?type=beta`

创建 Fine-grained token：

- **Token name**: `quartz-dispatch`
- **Repository access**: 只选 `<username>/quartz-site`
- **Permissions**: Contents → Read and write

### 6.2 将 PAT 添加到 vault 仓库 Secrets

```bash
gh secret set QUARTZ_REPO_TOKEN -R <username>/obsidian-vault
# 粘贴 token，回车
```

### 6.3 创建 notify workflow

在 obsidian-vault 仓库中：

```bash
cd ~/path/to/your-vault
mkdir -p .github/workflows
cat > .github/workflows/notify.yml << 'EOF'
name: Notify Quartz
on:
  push:
    branches: [main]
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -X POST \
            -H "Authorization: token ${{ secrets.QUARTZ_REPO_TOKEN }}" \
            -H "Accept: application/vnd.github.v3+json" \
            https://api.github.com/repos/<username>/quartz-site/dispatches \
            -d '{"event_type":"vault-updated"}'
EOF

git add .github/workflows/notify.yml
git commit -m "feat: auto-trigger quartz-site build on push"
git push origin main
```

> 将 `<username>` 替换为你的 GitHub 用户名。

---

## 第七步：验证完整流水线

1. 在 Obsidian 中编辑或新建一篇笔记（放在非 ignore 的目录下）
2. 提交并推送到 obsidian-vault
3. 观察 quartz-site 的 Actions 是否自动触发
4. 等待部署完成，刷新站点页面确认更新

```bash
# 监控 quartz-site 的 workflow
gh run list -R <username>/quartz-site --workflow=deploy.yml --limit 3
```

---

## 常见问题

### Q: 访问站点显示 RSS XML 而不是页面

**A**: vault 根目录缺少 `index.md`。创建一个带 title 的 index.md 作为首页，push 后重新构建。

### Q: 访问站点显示 404「私有笔记或笔记不存在」

**A**: 同上，缺少 `index.md`。

### Q: SSH 推送 GitHub 失败 (Connection closed port 22)

**A**: 国内网络可能阻断 SSH 端口。改用 HTTPS remote，或在 `~/.ssh/config` 配置 SSH 走 443 端口。

### Q: git push 被拒绝 (remote contains work)

**A**: 远端有初始 README。执行：

```bash
git pull origin main --allow-unrelated-histories --no-rebase
```

### Q: GitHub Actions 未触发

**A**: 检查 deploy.yml 中的 `branches` 是否与实际分支名一致（如 `v5` 不是 `v4`）。

### Q: 关系图谱为空

**A**: 正常现象。关系图谱依赖笔记间的 `[[双链]]`，在笔记中使用 `[[其他笔记名]]` 互相引用即可生成图谱。

### Q: 如何手动触发构建

**A**: deploy.yml 已包含 `workflow_dispatch` 触发器：

```bash
gh workflow run deploy.yml -R <username>/quartz-site --ref v5
```

### Q: 如何过滤不想公开的笔记

**A**: 在 `quartz.config.default.yaml` 的 `ignorePatterns` 中添加文件夹路径，支持嵌套路径如 `随笔/日记`。

---

## 目录结构参考

```
obsidian-vault (私有)            quartz-site (公开)
├── .github/                     ├── .github/
│   └── workflows/               │   └── workflows/
│       └── notify.yml           │       └── deploy.yml
├── .gitignore                   ├── quartz.config.default.yaml
├── index.md (首页)              ├── package.json
├── SRE/                         ├── quartz/
├── linux/                       │   ├── components/
├── homelab/                     │   ├── plugins/
├── private/ (被忽略)            │   └── ...
├── 随笔/                        └── ...
│   └── 日记/ (被忽略)
└── ...
```