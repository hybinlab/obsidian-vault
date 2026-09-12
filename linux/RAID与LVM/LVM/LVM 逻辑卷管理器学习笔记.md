---
tags:
  - linux
  - LVM
publish: true
---
## 一、为什么需要 LVM

传统分区（fdisk）一旦创建，大小就固定了。业务增长后磁盘空间不够，要么加盘重新分区，要么备份数据重建，非常麻烦。

LVM（Logical Volume Manager）在物理磁盘和文件系统之间加了一层抽象，允许动态扩容、缩容，不需要停机重新分区。

## 二、核心概念

```
物理磁盘/分区
    ↓ pvcreate
PV（Physical Volume，物理卷）
    ↓ vgcreate
VG（Volume Group，卷组）—— 存储资源池
    ↓ lvcreate
LV（Logical Volume，逻辑卷）—— 最终挂载使用的设备
```

- **PV**：被标记为 LVM 可用的磁盘或分区，是 LVM 的最底层单元
- **PE**（Physical Extent）：PV 被切分成的固定大小的块（默认 4MB），是 LVM 分配空间的最小单位
- **VG**：一个或多个 PV 组成的存储池，所有 PE 汇总在一起
- **LV**：从 VG 中分配若干 PE 组成的逻辑设备，格式化后挂载使用，路径为 `/dev/卷组名/逻辑卷名`

## 三、常用命令

|操作|物理卷（PV）|卷组（VG）|逻辑卷（LV）|
|---|---|---|---|
|扫描|pvscan|vgscan|lvscan|
|创建|pvcreate|vgcreate|lvcreate|
|显示|pvdisplay|vgdisplay|lvdisplay|
|删除|pvremove|vgremove|lvremove|
|扩展|—|vgextend|lvextend|
|缩小|—|vgreduce|lvreduce|

## 四、实操流程

### 4.1 创建 LVM

```bash
# 1. 创建物理卷
pvcreate /dev/sdb /dev/sdc

# 2. 创建卷组（名为 storage）
vgcreate storage /dev/sdb /dev/sdc

# 3. 查看卷组信息
vgdisplay storage

# 4. 创建逻辑卷（名为 vo，大小 150M）
lvcreate -n vo -L 150M storage
# 或按 PE 数量创建：lvcreate -n vo -l 37 storage

# 5. 格式化
mkfs.ext4 /dev/storage/vo

# 6. 挂载
mkdir /data
mount /dev/storage/vo /data

# 7. 写入 fstab（用 UUID）
blkid /dev/storage/vo
echo 'UUID=xxx  /data  ext4  defaults  0  2' >> /etc/fstab
```

### 4.2 扩容 LV

LVM 最大的优势，可以在线扩容，不需要卸载。

```bash
# 扩展逻辑卷（增加 100M）
lvextend -L +100M /dev/storage/vo

# 同步文件系统大小
# ext4 用 resize2fs
resize2fs /dev/storage/vo
# xfs 用 xfs_growfs
xfs_growfs /data
```

### 4.3 缩容 LV

**注意：xfs 不支持缩容，ext4 可以但必须先卸载。**

```bash
# 卸载
umount /data

# 检查文件系统
e2fsck -f /dev/storage/vo

# 先缩文件系统
resize2fs /dev/storage/vo 100M

# 再缩逻辑卷
lvreduce -L 100M /dev/storage/vo

# 重新挂载
mount /dev/storage/vo /data
```

缩容顺序不能反：必须先缩文件系统再缩 LV，否则数据会被截断损坏。

### 4.4 扩展 VG（加盘）

```bash
# 新盘创建 PV
pvcreate /dev/sdd

# 加入现有卷组
vgextend storage /dev/sdd

# 现在 VG 空间变大了，可以继续 lvextend
```

### 4.5 删除 LVM（逆序操作）

```bash
umount /data
lvremove /dev/storage/vo
vgremove storage
pvremove /dev/sdb /dev/sdc
```

## 五、LVM-Thin（精简配置）

普通 LV 创建时立即分配空间，Thin LV 按实际写入量分配，支持超分。

PVE 默认用的就是 LVM-Thin：给 VM 分配 32G 磁盘，实际只占用已写入的部分。好处是空间利用率高，风险是超分过多可能导致空间耗尽。

## 六、LVM vs RAID

|维度|LVM|RAID|
|---|---|---|
|核心目标|灵活管理空间|冗余和/或性能|
|数据保护|无冗余，拔盘即丢数据|有冗余（RAID 1/5/6/10）|
|动态扩容|支持|不方便|
|常见搭配|底层 RAID + 上层 LVM|—|

两者解决不同问题，不冲突。生产环境常见做法：RAID 保底层冗余 → LVM 做上层灵活管理。

## 七、注意事项

- LVM 没有冗余，不能替代 RAID 或备份
- 扩容安全（先扩 LV 再扩文件系统），缩容危险（先缩文件系统再缩 LV，且 xfs 不支持缩容）
- 云服务器（如阿里云 ECS）底层已有多副本 + LVM 管理，一般不需要手动折腾
- fstab 写 UUID 而不是设备路径