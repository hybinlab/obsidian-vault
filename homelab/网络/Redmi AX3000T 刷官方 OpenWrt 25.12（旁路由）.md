---
publish: true
---
# Redmi AX3000T 刷官方 OpenWrt 25.12（旁路由）

# Redmi AX6000 刷官方 OpenWrt 25.12（旁路由）完整记录

> 更新时间：2026-07-07
>
> 固件：官方 OpenWrt 25.12.x（APK 包管理）
>
> 硬件：Redmi AX6000


---

# 一、固件选择

下载官方 Stable Release。

官方固件：

<https://firmware-selector.openwrt.org/>

建议：

* 不要刷 Snapshot
* 直接选择当前 Stable（25.12.x）
* 下载 sysupgrade.bin


---

# 二、首次登录

默认地址：

```
192.168.1.1
```

默认：

```
用户名：root
密码：空
```


---

# 三、旁路由配置

LAN：

```
IP
192.168.31.11
```

Subnet：

```
255.255.255.0
```

Gateway：

```
192.168.31.1
```


---

## Advanced Settings

必须：

```
✔ Use default gateway
```

### 重点！！！

这里有一个坑：

```
Use custom DNS servers
```

官方 OpenWrt 25.12 默认可能是：

```
✔ 已勾选
但是 DNS 是空的
```

这样会导致：

```
ping 1.1.1.1
正常

ping baidu.com
Bad address

apk update
失败
```

原因：

dnsmasq 没有任何上游 DNS。

解决：

要么

```
取消勾选
```

要么填写

```
223.5.5.5

119.29.29.29
```

保存即可恢复。

这是本次折腾最大的坑。


---

# 四、DHCP

LAN

DHCP

```
Enable
```

即可。


---

# 五、确认 DNS 正常

测试：

```
ping 223.5.5.5
```

正常。

再测试：

```
nslookup baidu.com 223.5.5.5
```

如果返回 IP：

说明 DNS 没问题。

最后：

```
ping baidu.com
```

成功。

然后：

```
apk update
```

正常。


---

# 六、安装中文

```
apk add luci-i18n-base-zh-cn
```


---

# 七、安装 Argon

GitHub：

<https://github.com/jerrykuku/luci-theme-argon/releases>

下载：

```
luci-theme-argon-*.apk
```

上传：

```
System
Software
Upload Package
```

由于第三方 APK 未签名，

不能直接安装。

SSH：

```
apk add --allow-untrusted /tmp/upload.apk
```

或者：

```
apk add --allow-untrusted /tmp/luci-theme-argon-*.apk
```

安装完成。

切换主题：

```
uci set luci.main.mediaurlbase='/luci-static/argon'
uci commit luci
/etc/init.d/uhttpd restart
```


---

# 八、安装 OpenClash

GitHub：

<https://github.com/vernesong/OpenClash/releases>

下载：

```
luci-app-openclash-*.apk
```

不要下载：

```
ipk
```

官方 OpenWrt 25.x 使用 APK。

上传：

```
System
Software
Upload Package
```

SSH：

```
apk add --allow-untrusted /tmp/luci-app-openclash-*.apk
```

安装成功会自动：

* dnsmasq → dnsmasq-full
* bash
* curl
* ruby
* ip-full
* kmod-tun

等依赖。

无需手动安装。

OpenClash 官方仓库： <https://github.com/vernesong/OpenClash> :contentReference\[oaicite:0\]{index=0}


---

# 九、首次进入 OpenClash

进入：

```
服务
OpenClash
```

第一次：

下载

```
Meta Core
```

然后：

导入机场订阅。


---

# 十、第三方 APK 安装方式（官方 OpenWrt 25.x）

统一流程：

下载 APK

↓

上传

```
System
Software
Upload Package
```

↓

SSH

```
apk add --allow-untrusted /tmp/xxx.apk
```

以后：

* Argon
* OpenClash
* 其他第三方 LuCI 插件

全部采用该方式。


---

# 十一、常用命令

更新软件源：

```
apk update
```

安装：

```
apk add 包名
```

安装第三方：

```
apk add --allow-untrusted xxx.apk
```

查看包：

```
apk search 包名
```

卸载：

```
apk del 包名
```

查看文件：

```
ls /tmp
```


---

# 十二、今晚踩过的坑

## ① LAN 勾选了自定义 DNS 但为空

现象：

```
ping baidu.com

Bad address
```

原因：

没有上游 DNS。

解决：

取消勾选

或者填写：

```
223.5.5.5
```


---

## ② Argon 官方仓库没有

```
apk add luci-theme-argon
```

提示：

```
no such package
```

原因：

Argon 不属于官方软件源。

解决：

GitHub Release 下载 APK。


---

## ③ 第三方 APK 无法安装

提示：

```
UNTRUSTED signature
```

解决：

```
apk add --allow-untrusted xxx.apk
```


---

## ④ OpenClash 安装

直接安装官方 Release 的 APK。

依赖会自动安装。

无需按照旧教程手动安装十几个包（除非官方文档明确要求对应场景）。当前官方 Release 已提供 APK 包，适用于 APK 包管理器环境。:contentReference\[oaicite:1\]{index=1}


---

# 十三、后续建议

安装完成后：

* 设置 root 密码
* 下载 Meta Core
* 导入订阅
* 配置 Fake-IP
* 配置 DNS
* 配置绕过大陆模式
* 配置 IPv6（按需求）