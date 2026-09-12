
---
tags:
  - VPN
  - 排障
---
## 真正的 DNS 泄露是什么

例如你本来应该走：

```text
浏览器
 ↓
OpenClash
 ↓
1.1.1.1
 ↓
代理
```

结果实际上变成：

```text
浏览器
 ↓
中国移动DNS
 ↓
运营商
```

这样运营商能看到：

* 你访问过什么域名
* 访问时间
* DNS 请求记录

这才叫 DNS 泄露。


---

## 对于 OpenClash 用户，最可靠的判断方法

### 第一关：看 DNS 服务器

Windows：

```cmd
nslookup www.google.com
```

如果看到：

```text
Server: 192.168.31.3
```

或者：

```text
Server: OpenWrt
Address: 192.168.31.3
```

说明：

```text
PC
 ↓
OpenWrt
```

没绕过旁路由。

你的测试已经通过。


---

### 第二关：看 Fake-IP

如果返回：

```text
198.18.x.x
```

例如：

```text
198.18.0.4
```

说明：

```text
PC
 ↓
OpenClash DNS
```

已经被 Clash 接管。

你的测试也通过。


---

### 第三关：看真实出口 IP

访问：

```text
https://ip.sb
```

或者：

```text
https://ipleak.net
```

只要看到：

```text
54.212.x.x
2600:1f14:x:x
```

（你的 VPS）

而不是：

```text
中国移动
中国电信
中国联通
```

说明流量没泄露。


---

### 第四关：WebRTC

这是最容易忽略的。

访问：

```text
https://browserleaks.com/webrtc
```

如果看到：

```text
54.212.x.x
2600:1f14:x:x
```

正常。

如果看到：

```text
你的家庭宽带IP
```

那是真泄露。


---

### 第五关：抓包（最终判定）

这是唯一绝对准确的方法。

在 OpenWrt：

```bash
tcpdump -i br-lan port 53
```

然后电脑打开：

```text
google.com
youtube.com
github.com
```

观察。

正常情况：

```text
192.168.31.41
→
192.168.31.3
```

只有发往 OpenWrt 的 DNS。

不应该看到：

```text
192.168.31.41
→
120.232.x.x:53
```

或者：

```text
192.168.31.41
→
223.5.5.5:53
```

如果出现这种，才是真 DNS 泄露。


---