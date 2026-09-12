---
publish: true
---

# PVE 硬盘挂载操作手册

## 前置：查看硬盘信息

```bash
# 在 PVE 宿主机上
lsblk                    # 查看所有块设备和挂载点
blkid /dev/sdX1          # 查看分区文件系统类型和 UUID
```


---

## 一、挂载到 PVE 宿主机

```bash
# 创建挂载点
mkdir -p /mnt/diskname

# 手动挂载（临时，重启失效）
mount /dev/sdX1 /mnt/diskname

# NTFS 硬盘
mount -t ntfs-3g /dev/sdX1 /mnt/diskname
```

### 设置开机自动挂载（/etc/fstab）

```bash
# ext4

echo 'UUID=xxxxxxxx /mnt/diskname ext4 defaults,nofail 0 0' >> /etc/fstab

# NTFS

echo 'UUID=xxxxxxxx /mnt/diskname ntfs-3g defaults,nofail 0 0' >> /etc/fstab
```

> `nofail`：硬盘不存在时不阻止系统启动。UUID 从 `blkid` 获取。

验证 fstab：

```bash

mount -a
```


---

## 二、透传给 LXC 容器（Bind Mount）

**前提：硬盘已挂载到宿主机。**

```bash
# 停止容器
pct stop <CTID>

# 添加挂载点（宿主机路径 → 容器内路径）
pct set <CTID> -mp0 /mnt/diskname,mp=/mnt/diskname

# 多块硬盘依次用 -mp1 -mp2 ...
pct set <CTID> -mp1 /mnt/disk2,mp=/mnt/disk2

# 启动容器
pct start <CTID>
```

验证：

```bash
# 进容器确认
pct exec <CTID> -- ls /mnt/diskname
```

### 查看已配置的挂载点

```bash

cat /etc/pve/lxc/<CTID>.conf | grep mp
```

### 删除挂载点

```bash

pct set <CTID> -delete mp0
```


---

## 三、透传给 VM（虚拟机）

VM 不支持 bind mount，有两种方式：

### 方式 A：将整块硬盘作为直通设备（推荐）

```bash
# 停止 VM

qm stop <VMID>

# 添加硬盘直通（SATA 接口，编号从 0 开始）
qm set <VMID> -sata1 /dev/sdX

# 或 VirtIO 接口（性能更好）
qm set <VMID> -virtio1 /dev/sdX

# 启动 VM

qm start <VMID>
```

> VM 内部会看到一块新硬盘，需要在 VM 的操作系统内自行挂载。

### 方式 B：NFS/Samba 共享（适合跨系统访问）

在宿主机或另一台机器上搭 NFS/Samba，VM 内通过网络挂载，不在本文范围内。


---

## 四、在 LXC 内的 Docker 容器使用挂载的硬盘

硬盘透传进 LXC 后，在 `docker-compose.yml` 中直接映射：

```yaml

volumes:
  - /mnt/diskname/yourfolder:/data
```


---

## 五、常见问题

### LXC 内 Docker 启动报 AppArmor 错误

```
apparmor_parser: Access denied. You need policy admin privileges to manage profiles.
```

原因：LXC 容器内无法向内核加载 AppArmor profile。

解决：在 `docker-compose.yml` 每个服务下加：

```yaml

security_opt:
  - apparmor:unconfined
```

如需全局生效，在宿主机 LXC 配置里加（需重启 LXC）：

```bash

echo 'lxc.apparmor.profile: unconfined' >> /etc/pve/lxc/<CTID>.conf

pct stop <CTID> && pct start <CTID>
```

> 注意：`lxc.apparmor.profile: unconfined` 会覆盖 `features: nesting`，但不影响 Docker 正常使用。

### NTFS 硬盘权限问题

NTFS 不支持 Linux 原生权限模型，挂载时可以指定 uid/gid：

```bash

mount -t ntfs-3g -o uid=1000,gid=1000 /dev/sdX1 /mnt/diskname
```

### 硬盘挂载了但 LXC 看不到

检查 LXC 是否在宿主机挂载之前就启动了，需要确保 fstab 挂载顺序在 LXC 启动之前完成。