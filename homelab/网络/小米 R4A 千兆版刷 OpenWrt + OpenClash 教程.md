> 适用型号：小米路由器 4A 千兆版
> CPU：MediaTek MT7621
> 内存：64MB（够用，装 OpenClash 后注意内存监控）
> 日期：2026-09-04

---

## ⚠️ 风险提示

- 刷机有变砖风险
- 务必**先备份原始固件**再操作
- 错刷固件可能导致路由器永久损坏
- 建议手边备一台能上网的设备查问题

---

## 准备工作

### 工具准备

| 工具 | 用途 | 下载 |
|---|---|---|
| Breed 引导 | 不死鸟 Bootloader，刷机救砖 | breed-mt7621-pbr-m1.bin |
| OpenWrt 固件 | 主系统 | openwrt-ramips-mt7621-xiaomi_mir4a-gigabit-squashfs-sysupgrade.bin |
| ShellClash | OpenClash 的命令行替代品（资源占用低） | ShellClash.tar.gz |

### 网络环境

- 把电脑和路由器用网线直连
- 电脑 IP 设为自动获取或静态 `192.168.1.100`

---

## 第一步：利用漏洞进 SSH

小米 R4A 千兆版有远程命令执行漏洞，可以直接获取 SSH 权限。

### 1.1 工具下载

```bash
git clone https://github.com/acecil/mi-router-exploit.git
cd mi-router-exploit
pip install -r requirements.txt
```

### 1.2 执行漏洞利用

```bash
python remote_command_execution_vulnerability.py
# 输入路由器后台 IP：192.168.31.1（默认）
# 输入路由器管理密码
# 选择 1（启用 SSH）
```

### 1.3 SSH 连接路由器

```bash
ssh root@192.168.31.1
# 默认密码：admin（或管理后台密码）
```

如果进不去，路由器管理页面里**关闭防火墙**后再试。

---

## 第二步：备份原厂固件

**这一步必做，备份出错可以救砖。**

```bash
# 在路由器 SSH 里执行
cat /proc/mtd
# 记下 mtd0 / mtd1 / mtd4 的位置

dd if=/dev/mtd0 of=/tmp/all.bin
dd if=/dev/mtd1 of=/tmp/Bootloader.bin
dd if=/dev/mtd4 of=/tmp/eeprom.bin
```

用 SCP 工具（WinSCP、scp 命令）下载这三个文件到电脑保存：

```bash
# 从电脑执行
scp root@192.168.31.1:/tmp/all.bin ./
scp root@192.168.31.1:/tmp/Bootloader.bin ./
scp root@192.168.31.1:/tmp/eeprom.bin ./
```

---

## 第三步：刷入 Breed 引导

### 3.1 上传 Breed

把 `breed-mt7621-pbr-m1.bin` 上传到 `/tmp/`：

```bash
scp breed-mt7621-pbr-m1.bin root@192.168.31.1:/tmp/
```

### 3.2 写入 Breed

```bash
# 在路由器 SSH 里
mtd -r write /tmp/breed-mt7621-pbr-m1.bin Bootloader
```

路由器会自动重启，重启后**断电**。

### 3.3 进入 Breed 控制台

1. 断电后按住 **reset 键不放**
2. 上电（继续按住 reset）
3. 等 5-10 秒后松开
4. 浏览器访问 `192.168.1.1`
5. 进入 Breed 控制台

---

## 第四步：在 Breed 里刷 OpenWrt

### 4.1 备份当前 eeprom

在 Breed 控制台里**先备份 eeprom**，点「备份 eeprom」下载保存。

### 4.2 上传 OpenWrt 固件

1. 选择「固件更新」→「常规固件」
2. 上传 OpenWrt 固件 + eeprom.bin
3. 勾选「同时刷入 eeprom」
4. 点击「上传」→「更新」
5. 等待 2-3 分钟，**不要断电**

### 4.3 启动验证

刷完后路由器黄灯不闪烁、蓝灯常亮表示成功。

浏览器访问 OpenWrt 后台（默认 IP 看固件说明，常见 `192.168.1.1` 或 `10.0.0.1`）。

默认用户名：`root`，密码：`password`（看具体固件）。

---

## 第五步：安装 OpenClash

### 方案 A：直接装 OpenClash（资源吃紧）

```bash
opkg update
opkg install coreutils-nohup bash iptables dnsmasq-full curl ca-certificates ipset ip-full libcap libcap-bin ruby ruby-yaml kmod-tun kmod-inet-diag unzip luci luci-base

# 上传 OpenClash ipk 包
opkg install /tmp/luci-app-openclash_xxx.ipk
```

### 方案 B：装 ShellClash（更省内存）

```bash
# 创建临时目录解压
mkdir -p /tmp/SC_tmp
tar -zxf '/tmp/ShellClash.tar.gz' -C /tmp/SC_tmp/
source /tmp/SC_tmp/init.sh
```

按提示选择安装源、安装目录、配置 Clash 内核。

### 方案 C：从 LuCI 界面装（如果已经刷完）

1. 后台「系统」→「软件包」
2. 刷新软件包列表
3. 搜索 `luci-app-openclash`
4. 点击安装

---

## 第六步：配置 OpenClash

### 6.1 添加订阅链接

1. 进入 OpenClash → 「配置订阅」
2. 粘贴机场的订阅链接
3. 点击「下载配置」

### 6.2 启动 OpenClash

1. 「运行状态」→「启动 OpenClash」
2. 等待 yacd 或 dashboard 面板打开
3. 选择节点，开启「运行」

### 6.3 配置局域网代理（可选）

在 OpenClash 设置里：

- 勾选「允许局域网连接」
- DNS 模式选「fake-ip」或「redir-host」
- 启用规则集

---

## 故障排查

### 刷完进不去系统

- 重新进 Breed → 重新刷一遍
- 确认固件型号对（千兆版和百兆版不同）

### 内存不足（OOM）

R4A 千兆版只有 64MB 内存，跑 OpenClash 容易 OOM。解决：

```bash
# 添加 swap
dd if=/dev/zero of=/tmp/swap bs=1M count=128
mkswap /tmp/swap
swapon /tmp/swap
echo '/tmp/swap none swap sw 0 0' >> /etc/fstab
```

### 无线信号差

- 重新刷一次 eeprom.bin
- 检查天线连接

### OpenClash 启动失败

- 看日志：`/tmp/openclash.log`
- 检查订阅链接是否有效
- 重新下载配置文件

---

## 刷回官方固件

如果需要恢复：

1. 进 Breed
2. 上传之前备份的 `all.bin`
3. 刷入即可

---

## 参考链接

- [恩山无线论坛 R4A 板块](https://www.right.com.cn/forum/forum-69-1.html)
- [OpenWrt 官方固件下载](https://downloads.openwrt.org/)
- [OpenClash 项目地址](https://github.com/vernesong/OpenClash)
- [ShellClash 项目地址](https://github.com/juewuy/ShellClash)
