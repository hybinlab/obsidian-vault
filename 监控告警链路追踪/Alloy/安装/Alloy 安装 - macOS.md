---
publish: true
tags:
  - 部署
  - 日志
cssclasses:
  - Alloy
---

对应 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里"部署方式回顾"那节，本地开发机调试配置语法用，不是给生产环境用的。

## 安装

用 Homebrew：

```shell
brew tap grafana/grafana
brew install grafana/grafana/alloy
```

## 升级

```shell
brew upgrade grafana/grafana/alloy
brew services restart grafana/grafana/alloy
```

## 卸载

```shell
brew uninstall grafana/grafana/alloy
```

## 配置文件位置

遵循 Homebrew 的前缀规则，用 `brew --prefix` 查当前系统的 Homebrew 安装根目录，再拼 `/etc/alloy/config.alloy`（跟 [[Alloy 采集日志发送到 Loki]] 里"加载配置"那步 `sudo cp config.alloy $(brew --prefix)/etc/alloy/config.alloy` 对得上）。服务本身也是走 `brew services` 管理，跟其他 Homebrew 装的后台服务（比如 PostgreSQL、Redis）操作方式一致。

## 相关笔记

- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 部署方式总览、当前场景判断
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Docker.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Linux.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Ansible.md]]
