---
publish: true
tags:
  - 日志
  - 部署
cssclasses:
  - Alloy
---

对应 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里"部署方式回顾"那节，多台机器批量部署时才划算，单机没必要用这个。

## Playbook

用官方 `grafana.grafana.alloy` role，来自 Grafana Ansible Collection：

```yaml
- name: Install Alloy
  hosts: all
  become: true

  tasks:
    - name: Install Alloy
      ansible.builtin.include_role:
        name: grafana.grafana.alloy
      vars:
        alloy_config: |
          prometheus.scrape "default" {
            targets = [{"__address__" = "localhost:12345"}]
            forward_to = [prometheus.remote_write.prom.receiver]
          }
          prometheus.remote_write "prom" {
            endpoint {
                url = "<YOUR_PROMETHEUS_PUSH_ENDPOINT>"
            }
          }
```

跑法很常规，跟 [[ansible/Ansible 概念.md]] 里写的 playbook 套路一样：`ansible-playbook alloy.yml`。核心变量是 `alloy_config`——直接把整份 `.alloy` 配置内容当字符串塞进这个变量，role 内部负责把内容写到目标机器的配置文件里、装二进制、起 systemd 服务。

## 验证

装完用 systemd 管理和验证：

```shell
sudo systemctl status alloy.service
```

> 这个 role 具体把配置文件写到哪个路径、二进制装在哪，取决于 role 版本和目标系统发行版，实际装完建议 `systemctl status alloy` 或者 `cat /etc/systemd/system/alloy.service` 看 `ExecStart` 确认真实路径，不要直接照抄网上的具体路径数字。

## 什么时候用得上

对应 homelab 的场景：如果以后要给多台机器批量装 Alloy（比如触发了"多节点"这个部署条件），这个 role 就是比手动 SSH 一台台装更省事的方式——正好也符合在 [[SRE/SRE 学习路径.md]] 里给 Ansible 定的角色："配置管理，装软件配置"。现在 homelab 只有单台机器采集日志，用不上，走 [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Docker.md]] 更简单。

## 相关笔记

- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 部署方式总览、当前场景判断
- [[ansible/Ansible 概念.md]] — playbook/role 基础
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Docker.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Linux.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - macOS.md]]
