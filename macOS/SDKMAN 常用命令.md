---
tags:
  - macos
---
# SDKMAN 常用命令

## 候选版本查询

```bash
sdk list                  # 查看所有支持的工具
sdk list java             # 查看 Java 可用版本
sdk list gradle           # 查看 Gradle 可用版本
```

## 安装

```bash
sdk install java                      # 安装最新稳定版
sdk install java 21.0.7-tem           # 安装指定版本
sdk install gradle 8.7                # 安装其他工具
```

## 版本切换

```bash
sdk use java 21.0.7-tem               # 当前终端临时切换
sdk default java 21.0.7-tem           # 设为全局默认版本
sdk current java                      # 查看当前使用的版本
sdk current                           # 查看所有工具的当前版本
```

## 卸载

```bash
sdk uninstall java 21.0.7-tem
```

## 更新

```bash
sdk update                            # 刷新候选版本列表
sdk upgrade java                      # 升级 Java 到最新稳定版
sdk upgrade                           # 升级所有工具
sdk selfupdate                        # 更新 SDKMAN 本身
```

## 环境管理（项目级）

在项目根目录创建 `.sdkmanrc` 文件，可锁定该项目使用的工具版本：

```bash
sdk env init                          # 生成 .sdkmanrc（记录当前版本）
sdk env install                       # 按 .sdkmanrc 安装所需版本
sdk env                               # 切换到 .sdkmanrc 指定的版本
sdk env clear                         # 恢复全局默认版本
```

`.sdkmanrc` 示例：

```
java=21.0.7-tem
gradle=8.7
```

## 其他

```bash
sdk help                              # 查看帮助
sdk version                           # 查看 SDKMAN 版本
sdk offline enable                    # 启用离线模式
sdk offline disable                   # 禁用离线模式
```

## 常用 JDK 发行版

| 标识 | 发行版 | 说明 |
|----|----|----|
| `-tem` | Temurin（Eclipse） | 推荐，社区主流 LTS |
| `-graalce` | GraalVM CE | 支持 native-image |
| `-amzn` | Corretto（Amazon） | AWS 场景常用 |
| `-zulu` | Zulu（Azul） | 商业支持版本 |