---
publish: true
---
#### 1. 准备工作：PVE 网络环境确认

* `vmbr0` (家庭局域网): **桥接到唯一的物理网口** (`enp5s0`)。PVE 的管理 IP 也在 `vmbr0` 上。
* `vmbr1` (互联网 WAN): **必须留空**（不桥接任何物理网口）。
* `vmbr2` (安全隔离区): 不桥接任何物理网口。

本指南将仅使用 `**vmbr0**` 作为 OpenWrt 的 **LAN 口/唯一出口**。

#### 2. 准备工作：获取 OpenWrt 镜像 (保持不变)


1. **下载镜像：** 访问 OpenWrt 官方下载站或国内镜像站。
2. **选择版本：** 导航到适用于 `x86/64` 的镜像。
3. **选择文件：** 您需要下载适用于 KVM 虚拟机的镜像。文件名通常包含 `generic-squashfs-combined-efi.img.gz` (UEFI 引导) 或 `generic-squashfs-combined.img.gz` (Legacy 引导)。
4. **解压：** 下载后，请将其解压，得到 `.img` 格式的磁盘镜像文件。
5. **上传：** 将此 `.img` 文件通过 SCP 或 SFTP (例如使用 MobaXterm 或 WinSCP) 上传到 PVE 主机的 `/root/` 目录中，方便后续导入。

#### 3. 步骤一：创建 OpenWrt 虚拟机 (VM)


1. 
   1. 在 PVE 界面右上角，点击 **"创建虚拟机"**。
   2. **"常规" (General) 选项卡：**
      * **名称：** `OpenWRT` (或您喜欢的任何名称)。
      * **VM ID：** (例如 `100`)。
   3. **"操作系统" (OS) 选项卡：**
      * 选择 **"不使用任何介质"** (Do not use any media)。
      * **Guest OS：** 类型 (Type) 选 `Linux`，版本 (Version) 选 `6.x` 或 `Other`。
   4. **"系统" (System) 选项卡：**
      * **BIOS：** 如果您下载的是 `efi` 镜像，请选择 `OVMF (UEFI)`。如果是 `combined` 镜像，`SeaBIOS` (默认) 通常也可以。
      * **QEMU 代理：** (QEMU Agent) **取消勾选**。OpenWrt 默认不安装此代理。
   5. **"磁盘" (Disks) 选项卡：**
      * **直接删除此磁盘**。点击 "Hard Disk (sata0)" 旁边的垃圾桶图标。我们稍后将导入我们自己的镜像。
   6. **"CPU" 选项卡：**
      * **核心 (Cores)：** 按照您的规划，输入 **4**。
   7. **"内存" (Memory) 选项卡：**
      * **内存 (MiB)：** 按照您的规划，输入 **2048** (即 2 GB)。
   8. **"网络" (Network) 选项卡 (配置 LAN)：**
      * **桥接 (Bridge)：** `vmbr0` (您的家庭局域网)。
      * **模型 (Model)：** `VirtIO (paravirtualized)` (性能最佳)。
   9. **"确认" (Confirm) 选项卡：**
      * 核对所有设置，点击 **"完成"**。**此时不要启动虚拟机！**


-----

#### 4. 步骤二：导入磁盘并配置单网卡


1. **导入磁盘镜像：**
   * 使用 `qm importdisk` 命令导入磁盘到 `local-lvm`

     ```bash
     # qm importdisk <VM ID> <源文件路径> <目标存储池>
     # 示例：
     qm importdisk 100 /root/openwrt-xxx.img local-lvm
     
     ```

     *(请将* `*100*` *替换为您的 VM ID，*`*openwrt-xxx.img*` *替换为您上传的 .img 文件名，*`*local-lvm*` *替换为您 PVE 的目标存储池，例如* `*local-zfs*` *或* `*local-lvm*`*)*
2. **挂载新磁盘 & 调整引导顺序：**
   * 命令执行完毕后，回到 PVE 网页界面。
   * 找到您新创建的 `OpenWRT` 虚拟机，进入 **"硬件" (Hardware)** 选项卡。
   * 您会看到一个标为 **"未使用的磁盘 0"** (Unused Disk 0) 的新条目。
   * **双击**该磁盘，在弹出的窗口中：
     * **总线/设备 (Bus/Device)：** 选择 `VirtIO Block` (如果 OpenWrt 版本支持) 或 `SATA`。`VirtIO` 性能最好。
     * 点击 **"添加" (Add)**。
3. **移除 WAN 接口配置 (关键修改)：**
   * 回到 **"硬件" (Hardware)** 选项卡。
   * **确保只有一个网络设备 (**`**net0**`**)**。
   * **请勿添加第二个网络设备**（`vmbr1` WAN 口）。因为您只有一个物理网卡，第二个虚拟接口是无用的。


-----

#### 5. 步骤三：启动及配置 OpenWrt (旁路由配置)


1. **检查硬件列表：** 确保只有一个网络设备 `net0` 桥接在 `vmbr0` 上。
2. **启动虚拟机** 并进入 **"控制台"**。
3. **修改 LAN 口 IP：**
   * 启动完成后，执行 `vi /etc/config/network`。
   * **将** `**option ipaddr**` **修改为 OpenWrt 的静态 IP**（例如 `192.168.31.3`）。
4. **配置旁路由网关 (核心修改)：**
   * 在 `config interface 'lan'` 块中，**新增** `gateway` 和 `dns` 配置，指向您的主路由器 IP (`192.168.31.1`)：

   <!-- end list -->

   ```lua
   config interface 'lan'
           option device 'br-lan'
           option proto 'static'
           option ipaddr '192.168.31.3'
           option netmask '255.255.255.0'
           option gateway '192.168.31.1'      # <-- 流量出口
           list dns '192.168.31.1'            # <-- DNS 出口
           ...
   ```
   * 保存并退出。
5. **重启服务：** 执行 `reboot`。
6. **后续操作：**
   * 访问 Web 界面。
   * **安装 OpenClash**。
   * **在 OpenWrt 防火墙中添加 NAT 伪装规则** (`iptables -t nat -I POSTROUTING -o eth0 -j MASQUERADE`)，确保流量能被转发。