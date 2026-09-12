# Git 常用命令使用指南

# Git 常用命令使用指南

## 目录

* [简介](#%E7%AE%80%E4%BB%8B)
* [基础配置](#%E5%9F%BA%E7%A1%80%E9%85%8D%E7%BD%AE)
  * [用户信息配置](#%E7%94%A8%E6%88%B7%E4%BF%A1%E6%81%AF%E9%85%8D%E7%BD%AE)
  * [编辑器配置](#%E7%BC%96%E8%BE%91%E5%99%A8%E9%85%8D%E7%BD%AE)
  * [别名配置](#%E5%88%AB%E5%90%8D%E9%85%8D%E7%BD%AE)
  * [代理配置](#%E4%BB%A3%E7%90%86%E9%85%8D%E7%BD%AE)
* [仓库操作](#%E4%BB%93%E5%BA%93%E6%93%8D%E4%BD%9C)
* [文件操作](#%E6%96%87%E4%BB%B6%E6%93%8D%E4%BD%9C)
* [提交管理](#%E6%8F%90%E4%BA%A4%E7%AE%A1%E7%90%86)
* [分支管理](#%E5%88%86%E6%94%AF%E7%AE%A1%E7%90%86)
* [远程仓库](#%E8%BF%9C%E7%A8%8B%E4%BB%93%E5%BA%93)
* [标签管理](#%E6%A0%87%E7%AD%BE%E7%AE%A1%E7%90%86)
* [历史查看](#%E5%8E%86%E5%8F%B2%E6%9F%A5%E7%9C%8B)
* [撤销操作](#%E6%92%A4%E9%94%80%E6%93%8D%E4%BD%9C)
* [合并与变基](#%E5%90%88%E5%B9%B6%E4%B8%8E%E5%8F%98%E5%9F%BA)
* [存储操作](#%E5%AD%98%E5%82%A8%E6%93%8D%E4%BD%9C)
* [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)
* [最佳实践](#%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5)

## 简介

Git是一个分布式版本控制系统，用于跟踪文件的变化，协调多人协作开发。它能够记录文件的修改历史，支持分支管理，是现代软件开发中不可或缺的工具。

## 基础配置

### 用户信息配置

```bash
# 设置全局用户名和邮箱
git config --global user.name "您的姓名"
git config --global user.email "您的邮箱@example.com"

# 设置当前仓库的用户名和邮箱
git config user.name "您的姓名"
git config user.email "您的邮箱@example.com"

# 查看配置信息
git config --list
git config user.name
git config user.email
```

### 编辑器配置

```bash
# 设置默认编辑器
git config --global core.editor "code"  # VS Code
git config --global core.editor "vim"   # Vim
git config --global core.editor "notepad"  # Windows记事本
```

### 别名配置

```bash
# 设置常用命令别名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
```

### 代理配置

```bash
# 设置HTTP代理
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# 设置SOCKS5代理
git config --global http.proxy socks5://127.0.0.1:7890
git config --global https.proxy socks5://127.0.0.1:7890

# 设置代理认证（如果需要用户名密码）
git config --global http.proxy http://username:password@proxy-server:port

# 查看当前代理设置
git config --global --get http.proxy
git config --global --get https.proxy

# 删除代理设置
git config --global --unset http.proxy
git config --global --unset https.proxy

# 为特定域名设置代理（绕过代理）
git config --global http.https://github.com.proxy ""
git config --global http.https://gitee.com.proxy ""

# 设置代理超时时间
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999
```

## 仓库操作

### 创建仓库

```bash
# 初始化当前目录为Git仓库
git init

# 克隆远程仓库
git clone <repository-url>
git clone <repository-url> <directory-name>

# 克隆指定分支
git clone -b <branch-name> <repository-url>
```

### 仓库状态

```bash
# 查看仓库状态
git status

# 查看简短状态
git status -s
git status --short

# 忽略文件权限变化
git config core.fileMode false
```

## 文件操作

### 添加文件

```bash
# 添加单个文件
git add <filename>

# 添加多个文件
git add <file1> <file2>

# 添加所有文件
git add .

# 添加所有修改的文件
git add -A

# 交互式添加
git add -i
git add -p
```

### 删除文件

```bash
# 删除文件并添加到暂存区
git rm <filename>

# 删除文件但保留在工作区
git rm --cached <filename>

# 强制删除
git rm -f <filename>
```

### 移动/重命名文件

```bash
# 移动或重命名文件
git mv <old-filename> <new-filename>

# 移动文件到目录
git mv <filename> <directory>/
```

## 提交管理

### 提交更改

```bash
# 提交暂存区的更改
git commit -m "提交信息"

# 添加所有更改并提交
git commit -am "提交信息"

# 修改最后一次提交
git commit --amend

# 空提交（用于触发CI/CD）
git commit --allow-empty -m "空提交"
```

### 提交信息规范

```bash
# 推荐格式
git commit -m "feat: 添加用户登录功能"
git commit -m "fix: 修复登录验证bug"
git commit -m "docs: 更新README文档"
git commit -m "style: 格式化代码"
git commit -m "refactor: 重构用户模块"
git commit -m "test: 添加登录测试用例"
git commit -m "chore: 更新依赖包"
```

## 分支管理

### 分支操作

```bash
# 查看所有分支
git branch

# 查看所有分支（包括远程）
git branch -a

# 创建新分支
git branch <branch-name>

# 创建并切换到新分支
git checkout -b <branch-name>
git switch -c <branch-name>

# 切换到分支
git checkout <branch-name>
git switch <branch-name>

# 删除分支
git branch -d <branch-name>
git branch -D <branch-name>  # 强制删除

# 重命名分支
git branch -m <old-name> <new-name>
```

### 分支合并

```bash
# 合并分支到当前分支
git merge <branch-name>

# 禁用快进合并
git merge --no-ff <branch-name>

# 合并时显示详细信息
git merge --verbose <branch-name>
```

## 远程仓库

### 远程仓库管理

```bash
# 查看远程仓库
git remote -v

# 添加远程仓库
git remote add <name> <url>

# 修改远程仓库URL
git remote set-url <name> <new-url>

# 删除远程仓库
git remote remove <name>

# 重命名远程仓库
git remote rename <old-name> <new-name>
```

### 推送和拉取

```bash
# 推送到远程仓库
git push <remote> <branch>

# 推送所有分支
git push <remote> --all

# 推送标签
git push <remote> --tags

# 强制推送（谨慎使用）
git push <remote> <branch> --force

# 从远程拉取
git pull <remote> <branch>

# 拉取并变基
git pull --rebase <remote> <branch>
```

## 标签管理

### 标签操作

```bash
# 创建标签
git tag <tag-name>

# 创建带注释的标签
git tag -a <tag-name> -m "标签说明"

# 查看所有标签
git tag

# 查看标签详细信息
git show <tag-name>

# 删除标签
git tag -d <tag-name>

# 删除远程标签
git push <remote> --delete <tag-name>
```

## 历史查看

### 查看提交历史

```bash
# 查看提交历史
git log

# 查看简洁历史
git log --oneline

# 查看图形化历史
git log --graph --oneline --all

# 查看指定文件的修改历史
git log <filename>

# 查看指定作者的提交
git log --author="作者名"

# 查看指定时间段的提交
git log --since="2023-01-01" --until="2023-12-31"
```

### 查看差异

```bash
# 查看工作区与暂存区的差异
git diff

# 查看暂存区与最后一次提交的差异
git diff --staged
git diff --cached

# 查看两个提交之间的差异
git diff <commit1> <commit2>

# 查看两个分支之间的差异
git diff <branch1>..<branch2>
```

## 撤销操作

### 撤销工作区更改

```bash
# 撤销工作区的修改
git checkout -- <filename>
git restore <filename>

# 撤销所有工作区修改
git checkout -- .
git restore .
```

### 撤销暂存区更改

```bash
# 撤销暂存区的修改
git reset HEAD <filename>
git restore --staged <filename>

# 撤销所有暂存区修改
git reset HEAD
git restore --staged .
```

### 撤销提交

```bash
# 撤销最后一次提交（保留更改）
git reset --soft HEAD~1

# 撤销最后一次提交（保留工作区）
git reset --mixed HEAD~1
git reset HEAD~1

# 撤销最后一次提交（完全删除）
git reset --hard HEAD~1

# 创建新提交来撤销之前的提交
git revert <commit-hash>
```

## 合并与变基

### 合并策略

```bash
# 普通合并
git merge <branch-name>

# 快进合并
git merge --ff-only <branch-name>

# 禁用快进合并
git merge --no-ff <branch-name>

# 合并时解决冲突
git merge <branch-name>
# 解决冲突后
git add .
git commit
```

### 变基操作

```bash
# 变基到指定分支
git rebase <base-branch>

# 交互式变基
git rebase -i <commit-hash>

# 继续变基
git rebase --continue

# 跳过当前提交
git rebase --skip

# 中止变基
git rebase --abort
```

## 存储操作

### 暂存工作

```bash
# 暂存当前工作
git stash

# 暂存并添加说明
git stash push -m "暂存说明"

# 查看暂存列表
git stash list

# 应用暂存
git stash apply
git stash apply stash@{n}

# 应用并删除暂存
git stash pop
git stash pop stash@{n}

# 删除暂存
git stash drop stash@{n}
git stash clear
```

## 常见问题

### 解决合并冲突

```bash
# 1. 合并时发生冲突
git merge <branch-name>

# 2. 查看冲突文件
git status

# 3. 手动解决冲突
# 编辑冲突文件，删除冲突标记

# 4. 添加解决后的文件
git add <resolved-files>

# 5. 完成合并
git commit
```

### 找回丢失的提交

```bash
# 查看操作历史
git reflog

# 找到丢失的提交哈希
git show <commit-hash>

# 恢复丢失的提交
git checkout <commit-hash>
git checkout -b recovery-branch
```

### 清理仓库

```bash
# 清理未跟踪的文件
git clean -n  # 预览要删除的文件
git clean -f  # 删除未跟踪的文件
git clean -fd # 删除未跟踪的文件和目录

# 清理远程分支引用
git remote prune origin
```

## 最佳实践

### 提交规范


1. **使用清晰的提交信息**
   * 第一行：简短描述（50字符以内）
   * 空行
   * 详细描述（可选）
2. **遵循约定式提交**
   * feat: 新功能
   * fix: 修复bug
   * docs: 文档更新
   * style: 代码格式
   * refactor: 重构
   * test: 测试
   * chore: 构建过程或辅助工具的变动

### 分支管理策略


1. **主分支**
   * main/master: 生产环境代码
   * develop: 开发环境代码
2. **功能分支**
   * feature/功能名: 新功能开发
   * bugfix/问题描述: 问题修复
   * hotfix/问题描述: 紧急修复
3. **分支命名规范**
   * 使用小写字母和连字符
   * 描述性命名
   * 包含任务编号（如果有）

### 工作流程


1. **日常开发流程**

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/new-feature
   # 开发代码
   git add .
   git commit -m "feat: 添加新功能"
   git push origin feature/new-feature
   # 创建Pull Request
   ```
2. **代码审查**
   * 提交前进行自测
   * 使用Pull Request进行代码审查
   * 确保测试通过
3. **发布流程**
   * 合并到develop分支
   * 测试验证
   * 合并到main分支
   * 创建发布标签