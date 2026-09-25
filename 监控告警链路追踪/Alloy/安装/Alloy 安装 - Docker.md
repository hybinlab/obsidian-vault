---
publish: true
tags:
  - 日志
  - 部署
cssclasses:
  - Alloy
---

对应 [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] 里"部署方式回顾"那节，homelab 现在实际用的就是这种方式。

## 安装命令

```shell
docker run \
  -v <CONFIG_FILE_PATH>:/etc/alloy/config.alloy \
  -p 12345:12345 \
  grafana/alloy:latest \
    run --server.http.listen-addr=0.0.0.0:12345 --storage.path=/var/lib/alloy/data \
    /etc/alloy/config.alloy
```

- `-v <CONFIG_FILE_PATH>:/etc/alloy/config.alloy`：把宿主机上写好的配置文件挂进容器
- `-p 12345:12345`：暴露 UI/调试端口
- **`--server.http.listen-addr=0.0.0.0:12345` 这个参数必须显式加**——容器内默认只监听 `127.0.0.1`，不改成 `0.0.0.0` 的话，容器外（宿主机或者局域网）根本连不上 `12345` 端口，UI 打不开
- `--storage.path=/var/lib/alloy/data`：Alloy 自身状态数据存放路径，建议配合 `-v` 再挂一个卷出来做持久化（命令示例里没写，实际用的话记得加，不然容器重建状态就丢了）

## 最小可用配置

先跑起来再往里加组件：

```alloy
logging {
  level  = "info"
  format = "logfmt"
}
```

## 验证

浏览器访问 `http://localhost:12345`，UI 能打开就算成功。

## 对应 homelab 实际用法：Docker Compose

homelab 那份用的是 Docker Compose，效果一样，只是把这行 `docker run` 换成了 `docker-compose.yml` 里的 `services.alloy` 块，加了 `network_mode` 或自定义网络（这样才能用 `http://loki:3100` 这种容器名当地址访问，参考 [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] 里的实际配置）。

## 相关笔记

- [[监控告警链路追踪/Alloy/Grafana Alloy 概述.md]] — 部署方式总览、当前场景判断
- [[监控告警链路追踪/日志/Alloy 采集日志发送到 Loki.md]] — homelab 实际的 Docker Compose 配置
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Linux.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - Ansible.md]]
- [[监控告警链路追踪/Alloy/安装/Alloy 安装 - macOS.md]]
