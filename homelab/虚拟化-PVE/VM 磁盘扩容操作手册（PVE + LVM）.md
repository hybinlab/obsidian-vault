---
publish: true
---
# VM 磁盘扩容操作手册（PVE + LVM）

## 背景

在 PVE 层给虚拟机的磁盘扩容后，VM 内部看到的 `sda` 会立即变大（比如 100G），但分区、LVM 物理卷、逻辑卷和文件系统不会跟着自动变化，需要在 VM 内部一层层往外扩：

分区 `sda3` → LVM 物理卷 → 逻辑卷 → 文件系统

## 前提条件

* PVE 层的磁盘扩容已生效（VM 内 `lsblk` / `fsdisk -l` 能看到 `sda` 的新容量）
* VM 使用 LVM 管理根分区（`ubuntu-vg` / `ubuntu-lv` 为默认 Ubuntu cloud image 布局）
* 没有 `growpart` 命令时先安装：`apt install cloud-guest-utils`

---

## 操作步骤

在 Agent VM 内执行：

```bash
# 1. 把分区 sda3 扩到磁盘末尾
growpart /dev/sda 3

# 2. 让 LVM 物理卷识别新的大小
pvresize /dev/sda3

# 3. 把逻辑卷扩到全部剩余空间，-r 会顺带扩文件系统（ext4/xfs 都支持）
lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv

# 4. 确认结果
df -h /
```

完成后根分区容量应从 48G 左右变为约 97G。

---

## 注意事项

* 全程可在线操作，无需重启，不影响正在运行的服务（如 Hindsight）
* `growpart` 只扩分区表，不动分区内数据，安全可重复执行
* 若 `pvresize` 提示物理卷已是最大，说明分区没扩成功，检查第 1 步
* `lvextend -r` 依赖 `resize2fs`（ext4）或 `xfs_growfs`（xfs），系统里通常已自带
