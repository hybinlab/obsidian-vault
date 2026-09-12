---
tags:
  - linux
  - fdisk
publish: true
---

## 完整流程

```
查看磁盘 → 分区 → 格式化 → 挂载 → 写入 fstab
```

---

## 1. 查看磁盘信息

```bash
# 列出所有磁盘和分区
fdisk -l

# 查看块设备树
lsblk

# 查看 UUID
blkid
```

---

## 2. 分区操作（fdisk 交互模式）

```bash
fdisk /dev/sdb
```

### 常用命令

|命令|作用|
|---|---|
|`m`|显示帮助|
|`p`|打印当前分区表|
|`n`|新建分区|
|`d`|删除分区|
|`t`|修改分区类型|
|`l`|列出所有分区类型代码|
|`w`|写入并退出（不可逆）|
|`q`|不保存退出|

### 新建分区示例

```
Command: n
Partition type: p (主分区) 或 e (扩展分区)   ← 仅 MBR 分区表会问
Partition number: 1 (默认)
First sector: 回车 (默认)
Last sector: +50G (指定大小) 或 回车 (用完剩余空间)

Command: w   ← 确认写入
```

> MBR 最多 4 个主分区。需要更多分区时，建一个扩展分区（e），在里面划逻辑分区。 GPT 没有这个限制，不会出现 p/e 选项，直接建分区。

### 大小指定方式

|写法|含义|
|---|---|
|`+50G`|50 GiB|
|`+512M`|512 MiB|
|`+1T`|1 TiB|
|直接回车|使用全部剩余空间|

---

## 3. 让内核识别新分区

```bash
# 通知内核重新读取分区表（不用重启）
partprobe
```

---

## 4. 格式化

```bash
# ext4（最常用）
mkfs.ext4 /dev/sdb1

# XFS
mkfs.xfs /dev/sdb1

# FAT32（EFI 分区用）
mkfs.fat -F 32 /dev/sdb1

# NTFS
mkfs.ntfs -f /dev/sdb1    # -f 快速格式化
```

---

## 5. 挂载

```bash
# 创建挂载点
mkdir -p /mnt/data

# 临时挂载
mount /dev/sdb1 /mnt/data

# 验证
df -h | grep sdb1
```

---

## 6. 持久化挂载（写入 fstab）

```bash
# 查看 UUID
blkid /dev/sdb1

# 编辑 fstab
nano /etc/fstab

# 添加一行（用 UUID，不用设备名）
UUID=xxxx-xxxx  /mnt/data  ext4  defaults,nofail  0  2

# 测试 fstab 是否正确（不用重启）
mount -a
```

---

## fdisk vs cfdisk vs gdisk

|工具|特点|
|---|---|
|`fdisk`|命令行交互，MBR 和 GPT 都支持，`fdisk -l` 看信息最快|
|`cfdisk`|TUI 图形界面，直观好用，适合手动分区|
|`gdisk`|专门针对 GPT 分区表，操作逻辑同 fdisk|
|`parted`|支持调整已有分区大小，MBR/GPT 都行|

日常推荐：`fdisk -l` 看信息，`cfdisk` 做分区操作。

---

## 注意事项

- 分区操作前先 `lsblk` 确认目标磁盘，别搞错盘
- `w` 写入后不可逆，写入前用 `p` 再确认一遍
- 格式化会清除该分区所有数据
- fstab 写错可能导致开机卡住，改完一定用 `mount -a` 测试
- 外接盘、可选盘在 fstab 中加 `nofail`，设备不在时不阻塞启动
- 超过 2TB 的磁盘用 `gdisk` 或 `parted`，fdisk 对 GPT 的支持在老版本中不完善