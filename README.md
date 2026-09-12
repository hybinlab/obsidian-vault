# obsidian-vault

阿B 的个人 Obsidian 知识库，私有仓库，记录 Linux/网络/Homelab/自动化等技术笔记。

## 结构

顶层按主题分文件夹（`linux/`、`homelab/`、`VPN/`、`ansible/` 等），入口见 [[index]]。

## 同步方式

- PC：本地 Obsidian 直接 `git commit/push` 到这个仓库
- 手机：Syncthing 同步，不跑 git

## 发布机制

这个仓库是私有的，公开站点走 [[新知识库的构建]] 里定的方案：`quartz-site` 仓库通过 deploy key 拉这个仓库的内容再构建。

- **白名单**：笔记 frontmatter 写 `publish: true` 才会被收进构建
- **黑名单兜底**：`随笔/`、`年记/`、`渗透测试笔记/` 这几个目录在 CI 里硬删，不管有没有打 `publish`，都不会出现在公开站点

改动 vault 结构（加新主题文件夹、改私密目录名）时记得同步更新黑名单和 [[index]] 里的导航链接。
