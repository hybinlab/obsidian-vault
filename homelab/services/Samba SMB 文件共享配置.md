---
publish: true
tags:
  - homelab
  - 部署
---
## 环境

* **OS**: Ubuntu 24.04.4 LTS
* **主机名**: docker-host
* **共享目录**: `/mnt/jellyfin`（ext4，931.5G 外挂磁盘）
* **磁盘**: `/dev/sdc1`，UUID `3e35ecfe-5c6c-4f59-91a9-24aeb84e4557`

## 1. 挂载磁盘

```bash

mkdir -p /mnt/jellyfin

mount /dev/sdc1 /mnt/jellyfin
```

写入 fstab 实现开机自动挂载：

```bash
# /etc/fstab 追加
UUID=3e35ecfe-5c6c-4f59-91a9-24aeb84e4557 /mnt/jellyfin ext4 defaults,nofail 0 0
```

## 2. 安装 Samba

```bash

apt install samba
```

## 3. 配置共享

备份原始配置后追加共享段：

```bash

cp /etc/samba/smb.conf /etc/samba/smb.conf.bak

cat >> /etc/samba/smb.conf << 'EOF'

[media]
   path = /mnt/jellyfin
   browseable = yes
   read only = no
   guest ok = no
   create mask = 0644
   directory mask = 0755

EOF
```

各参数说明：

| 参数 | 值 | 作用 |
|----|----|----|
| `path` | `/mnt/jellyfin` | 共享的本地路径 |
| `browseable` | `yes` | 在网络邻居中可见 |
| `read only` | `no` | 允许写入 |
| `guest ok` | `no` | 禁止匿名访问 |
| `create mask` | `0644` | 新文件权限 |
| `directory mask` | `0755` | 新目录权限 |

## 4. 设置 SMB 用户

```bash

smbpasswd -a root
```

按提示输入密码。

## 5. 启动服务

```bash

systemctl restart smbd

systemctl enable smbd
```

## 6. 客户端访问

* **Windows**: 资源管理器地址栏输入 `\\<IP>\media`
* **macOS**: Finder → 前往 → 连接服务器 → `smb://<IP>/media`
* **Linux**: `mount -t cifs //<IP>/media /mnt/smb -o username=root,password=<密码>`

用户名 `root`，密码为 `smbpasswd` 设置的密码。