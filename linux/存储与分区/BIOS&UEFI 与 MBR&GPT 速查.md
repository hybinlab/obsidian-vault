---
tags:
  - 存储
  - linux
publish: true
---
## 两个不同层面

|层面|老方案|新方案|
|---|---|---|
|主板固件（开机第一个跑的程序）|BIOS|UEFI|
|分区表格式（磁盘怎么分区）|MBR|GPT|

---

## BIOS vs UEFI

||BIOS|UEFI|
|---|---|---|
|年代|1980s|2000s+|
|界面|文本，简陋|图形化，可用鼠标|
|引导方式|只能从 MBR 引导|从 EFI 分区引导|
|安全启动|无|支持 Secure Boot|
|启动速度|慢|快|
|现状|淘汰中，新主板通过 CSM/Legacy 模式兼容|主流|

---

## MBR vs GPT

||MBR|GPT|
|---|---|---|
|最大磁盘容量|2TB|18EB（几乎无限）|
|最大分区数|4 个主分区（或 3 主 + 1 扩展）|128 个分区|
|数据冗余|分区表只有一份，损坏即丢失|头尾各一份备份|
|现状|老系统、小磁盘还在用|推荐，现代标准|

---

## 配对关系

```
BIOS + MBR  → 传统组合，老电脑
UEFI + GPT  → 现代组合，推荐
BIOS + GPT  → 可以，需要 1M 的 BIOS boot 分区放 GRUB
UEFI + MBR  → 可以，通过 CSM 兼容模式
```

---

## 实际场景

### PVE 虚拟机（默认 BIOS 模式 + GPT）

```
/dev/sda1   1M    BIOS boot     ← GRUB 引导代码存放处
/dev/sda2   2G    /boot         ← 内核和引导文件
/dev/sda3   剩余   /            ← 系统根分区（通常在 LVM 上）
```

### 物理机（UEFI 模式 + GPT）

```
/dev/sda1   512M  EFI System    ← 挂载到 /boot/efi，FAT32 格式
/dev/sda2   2G    /boot         ← 内核和引导文件
/dev/sda3   剩余   /            ← 系统根分区
```

---

## 怎么判断当前系统用的哪种

```bash
# 判断固件类型
ls /sys/firmware/efi
# 存在 → UEFI，不存在 → BIOS

# 判断分区表类型
fdisk -l /dev/sda
# Disklabel type: gpt → GPT
# Disklabel type: dos → MBR
```

---

## 要点

- 超过 2TB 的磁盘必须用 GPT，MBR 识别不了
- UEFI 启动需要一个 FAT32 格式的 EFI 分区（通常 512M）
- BIOS + GPT 启动需要一个 1M 的 BIOS boot 分区（无文件系统，给 GRUB 用）
- PVE 创建 VM 默认是 BIOS 模式；如需 UEFI，创建 VM 时要手动选择 OVMF (UEFI) 固件并添加 EFI Disk