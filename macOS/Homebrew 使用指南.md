---
tags:
  - macos
---
## 安装

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

验证安装：

```bash

brew --version
```


---

## 常用命令

| 命令 | 说明 |
|----|----|
| `brew install <pkg>` | 安装 CLI 工具 |
| `brew install --cask <app>` | 安装 GUI 应用 |
| `brew uninstall <pkg>` | 卸载包 |
| `brew update` | 更新 Homebrew 本身 |
| `brew upgrade` | 升级所有已安装包 |
| `brew upgrade <pkg>` | 升级指定包 |
| `brew list` | 列出已安装包 |
| `brew search <keyword>` | 搜索包 |
| `brew info <pkg>` | 查看包信息 |
| `brew cleanup` | 清理旧版本缓存 |
| `brew doctor` | 诊断环境问题 |


---

## 卸载 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
```

确认干净：

```bash

which brew  # 无输出即已卸载
```