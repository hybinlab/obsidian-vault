---
publish: true
---
## 查看

```bash
timedatectl
```

## 修改

```bash
 timedatectl set-timezone Asia/Shanghai
```

## 验证

```bash
 date
```

如果是服务器批量初始化，可以直接写进初始化脚本：

```bash
 timedatectl set-timezone Asia/Shanghai
```

不过有两个例外：

* 极老系统（没有 systemd，例如 CentOS 6）：

```bash
 ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

* Docker/LXC 容器： 取决于容器是否有权限和是否安装了 systemd，很多时候直接挂载宿主机 /etc/localtime 更简单。

日常运维里，记住 timedatectl set-timezone 基本够用了。