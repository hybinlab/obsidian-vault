---
publish: true
tags:
  - Alloy
  - HTTP
  - 监听配置
---
## 问题

`/etc/alloy/config.alloy` 中配置：

```alloy
http {
  listen_address = "0.0.0.0"
  listen_port    = 12345
}
```

会导致 Alloy 启动失败：

```text
unrecognized attribute name "listen_address"
```

HTTP/UI 监听地址应通过 Alloy 启动参数配置。

## 处理

### 1. 备份

```bash
cp /etc/alloy/config.alloy /etc/alloy/config.alloy.bak
cp /etc/default/alloy /etc/default/alloy.bak
```

### 2. 删除错误配置

从 `/etc/alloy/config.alloy` 删除：

```alloy
http {
  listen_address = "0.0.0.0"
  listen_port    = 12345
}
```

验证配置：

```bash
alloy validate /etc/alloy/config.alloy
```

### 3. 配置监听地址

编辑：

```bash
vim /etc/default/alloy
```

修改：

```bash
CUSTOM_ARGS="--server.http.listen-addr=0.0.0.0:12345"
```

Ubuntu DEB 包的 systemd 服务会通过：

```text
/etc/default/alloy
```

读取 `CUSTOM_ARGS`。

### 4. 重启

```bash
systemctl restart alloy
systemctl status alloy --no-pager
```

检查监听：

```bash
ss -lntp | grep 12345
```

查看日志：

```bash
journalctl -u alloy -n 50 --no-pager
```

## 注意

如果之后仍出现：

```text
prometheus.remote_write.default
non-recoverable error
```

这是另一个问题，与 Alloy HTTP/UI 监听配置无关，需要继续检查 Prometheus Remote Write 接收端。