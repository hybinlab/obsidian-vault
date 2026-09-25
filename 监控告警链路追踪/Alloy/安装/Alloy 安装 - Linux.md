---
publish: true
tags:
  - 部署
  - 日志
cssclasses:
  - Alloy
---

对应 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里"部署方式回顾"，这是不用容器、直接在宿主机上装成系统服务的方式——采集宿主机本身（journal、`/var/log`）的场景比 Docker 更方便，见概述笔记里"要采集宿主机本身用系统服务更方便处理权限和路径"那条判断。

## Debian / Ubuntu（apt）

```shell
sudo mkdir -p /etc/apt/keyrings
sudo wget -O /etc/apt/keyrings/grafana.asc https://apt.grafana.com/gpg-full.key
sudo chmod 644 /etc/apt/keyrings/grafana.asc
echo "deb [signed-by=/etc/apt/keyrings/grafana.asc] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install alloy
```

## RHEL / Fedora（dnf/yum）

```shell
wget -q -O gpg.key https://rpm.grafana.com/gpg.key
sudo rpm --import gpg.key
echo -e '[grafana]\nname=grafana\nbaseurl=https://rpm.grafana.com\nrepo_gpgcheck=1\nenabled=1\ngpgcheck=1\ngpgkey=https://rpm.grafana.com/gpg.key\nsslverify=1\nsslcacert=/etc/pki/tls/certs/ca-bundle.crt' | sudo tee /etc/yum.repos.d/grafana.repo
yum update
sudo dnf install alloy
```

## SUSE / openSUSE（zypper）

```shell
wget -q -O gpg.key https://rpm.grafana.com/gpg.key
sudo rpm --import gpg.key
sudo zypper addrepo https://rpm.grafana.com grafana
sudo zypper update
sudo zypper -r grafana install alloy
```

三个发行版套路一致：导入 GPG key → 加官方仓库 → 装包，标准做法，跟平时装别的第三方软件源没区别。

## 配置文件位置

包管理器安装的版本，配置文件固定在 `/etc/alloy/config.alloy`（跟 [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] 里"加载配置"那步 `sudo cp config.alloy /etc/alloy/config.alloy` 对得上，这也是为什么 Docker 方式要手动挂载到同一个路径——保持跟包管理器安装版本的目录约定一致）。

## Systemd 服务管理

官方文档明确给出的只有 `stop`，其余是标准 systemd 管理套路，跟平时管理别的系统服务一样：

```shell
sudo systemctl start alloy      # 启动
sudo systemctl stop alloy       # 停止
sudo systemctl enable alloy     # 开机自启
sudo systemctl status alloy     # 查看状态
journalctl -u alloy -f          # 实时看日志
```

改了配置文件想热重载，走 [[监控告警链路追踪/Alloy/Alloy HTTP 接口参考.md]] 里的 `curl -X POST http://localhost:12345/-/reload`，不用 `systemctl restart`（重启会丢内存里的状态，重载不会）。

## 卸载

```shell
# Debian/Ubuntu
sudo systemctl stop alloy
sudo apt-get remove alloy
sudo rm -i /etc/apt/sources.list.d/grafana.list   # 可选，连仓库一起清

# RHEL/Fedora
sudo systemctl stop alloy
sudo dnf remove alloy
sudo rm -i /etc/yum.repos.d/grafana.repo           # 可选

# SUSE/openSUSE
sudo systemctl stop alloy
sudo zypper remove alloy
sudo zypper removerepo grafana                      # 可选
```

## 什么时候选这个而不是 Docker

跟 [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Docker.md]] 的取舍标准是同一条：容器化服务（比如给 Loki/Grafana 同网络的日志采集）用 Docker 更省事；要读宿主机的 `/var/log`、systemd journal、或者需要访问宿主机层面的资源（进程信息、挂载点）时，直接装系统服务权限和路径处理起来更直接，不用在 Docker 里折腾 volume 挂载宿主机路径。

## 相关笔记

- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 部署方式总览、当前场景判断
- [[监控告警链路追踪/Alloy/Alloy HTTP 接口参考.md]] — `/-/reload` 热重载
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Docker.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Ansible.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - macOS.md]]
