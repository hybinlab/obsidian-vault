## 一、快速安装（推荐）

### 方法1：使用订阅链接（最简单）

如果有订阅链接，直接在宝塔面板执行：

```bash
# 1. 下载 Clash
cd /tmp
wget https://github.com/Dreamacro/clash/releases/download/v1.18.0/clash-linux-amd64-v1.18.0.gz
gunzip clash-linux-amd64-v1.18.0.gz
chmod +x clash-linux-amd64-v1.18.0
sudo mv clash-linux-amd64-v1.18.0 /usr/local/bin/clash

# 2. 创建配置目录
mkdir -p ~/.config/clash
cd ~/.config/clash

# 3. 下载订阅配置（替换为你的订阅链接）
wget -O config.yaml "https://你的订阅链接"

# 4. 启动
clash -d ~/.config/clash &
```


---

## 二、手动配置代理

### 步骤1：通过宝塔面板上传 Clash


1. 打开宝塔面板 -> 文件管理
2. 进入 `/tmp` 目录
3. 通过文件上传功能上传 Clash 程序
4. 或者使用 SSH 执行上面的下载命令

### 步骤2：通过宝塔面板创建配置文件


1. 在宝塔文件管理中找到 `/root/.config/clash/` 目录（如果不存在就创建）
2. 新建文件 `config.yaml`
3. 复制以下内容并编辑：

```yaml
port: 7890
socks-port: 7891
allow-lan: true
mode: rule
log-level: info

external-controller: 127.0.0.1:9090

dns:
  enable: true
  nameserver:
    - 223.5.5.5
    - 119.29.29.29

proxies:
  - name: "你的代理"
    type: ss  # 或 vmess, trojan 等
    server: 你的服务器地址
    port: 443
    cipher: aes-256-gcm
    password: 你的密码

proxy-groups:
  - name: "节点选择"
    type: select
    proxies:
      - "你的代理"
      - DIRECT

rules:
  - DOMAIN-SUFFIX,google.com,节点选择
  - DOMAIN-SUFFIX,github.com,节点选择
  - GEOIP,CN,DIRECT
  - MATCH,节点选择
```

### 步骤3：通过宝塔终端启动

在宝塔面板打开"终端"功能，执行：

```bash
# 启动 Clash（前台）
clash -d ~/.config/clash

# 或后台运行
nohup clash -d ~/.config/clash > /tmp/clash.log 2>&1 &

# 查看日志
tail -f /tmp/clash.log
```


---

## 三、使用方法

### 设置代理环境变量

在终端执行：

```bash
# 临时设置（当前终端）
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890

# 永久设置（添加到 ~/.bashrc）
echo 'export http_proxy=http://127.0.0.1:7890' >> ~/.bashrc
echo 'export https_proxy=http://127.0.0.1:7890' >> ~/.bashrc
source ~/.bashrc
```

### 测试代理

```bash
# 测试 HTTP 代理
curl -x 127.0.0.1:7890 https://www.google.com

# 测试环境变量代理
curl https://www.google.com
```

### 取消代理

```bash
unset http_proxy https_proxy
```


---

## 四、通过宝塔面板管理 Clash

### 使用宝塔进程守护功能


1. 宝塔面板 -> 软件商店 -> 安装"进程守护管理器"
2. 添加进程：
   * 进程名称：clash
   * 启动命令：`/usr/local/bin/clash -d /root/.config/clash`
   * 工作目录：`/root/.config/clash`

这样 Clash 崩溃后会自动重启。

### 设置开机自启

在宝塔"计划任务"中添加：

```bash
# 任务类型：Shell 脚本
# 任务名称：启动 Clash
# 执行周期：N分钟（N=1）
# 脚本内容：
nohup /usr/local/bin/clash -d /root/.config/clash > /dev/null 2>&1 &
```


---

## 五、查看代理状态

### 通过 RESTful API

Clash 提供了 API 接口（127.0.0.1:9090），可以通过 curl 查询：

```bash
# 查看所有代理
curl http://127.0.0.1:9090/proxies

# 查看流量统计
curl http://127.0.0.1:9090/traffic

# 切换代理节点
curl -X PUT http://127.0.0.1:9090/proxies/节点选择 \
  -d '{"name":"代理名称"}'
```


---

## 六、防火墙设置（重要）

在宝塔面板 -> 安全 中开放以下端口：

* **7890** - HTTP 代理端口
* **7891** - SOCKS5 代理端口
* **9090** - RESTful API 端口（仅本地）

如果只需要本地使用，可以不用开放。


---

## 七、常见问题

### Q1: 如何查看 Clash 是否运行？

```bash
ps aux | grep clash
```

### Q2: 如何停止 Clash？

```bash
pkill clash
# 或
killall clash
```

### Q3: 如何查看日志？

通过宝塔文件管理器查看：`~/.config/clash/clash.log`

或在终端：

```bash
tail -f ~/.config/clash/clash.log
```

### Q4: 配置了代理但无法连接外网？

检查代理配置是否正确：

```bash
# 测试本地端口是否监听
netstat -tlnp | grep 7890
```

### Q5: 如何在特定程序中使用代理？

使用 proxychains：

```bash
# 安装
yum install proxychains -y  # CentOS
apt install proxychains -y   # Ubuntu/Debian

# 配置
vi /etc/proxychains.conf
# 添加：socks5 127.0.0.1 7891

# 使用
proxychains curl https://www.google.com
```


---

## 八、代理类型配置示例

### Shadowsocks (SS)

```yaml
proxies:
  - name: "SS代理"
    type: ss
    server: ss.example.com
    port: 8388
    cipher: aes-256-gcm
    password: your-password
```

### Vmess (V2Ray)

```yaml
proxies:
  - name: "Vmess代理"
    type: vmess
    server: vm.example.com
    port: 443
    uuid: your-uuid-here
    alterId: 0
    cipher: auto
    tls: true
```

### Trojan

```yaml
proxies:
  - name: "Trojan代理"
    type: trojan
    server: trojan.example.com
    port: 443
    password: your-password
    sni: your-domain.com
```


---

## 九、更新订阅

如果有订阅链接，可以通过宝塔计划任务自动更新：

```bash
# 计划任务中添加
cd ~/.config/clash
wget -O config.yaml.new "https://你的订阅链接"
mv config.yaml config.yaml.bak
mv config.yaml.new config.yaml
# 重启 Clash
pkill clash
nohup clash -d ~/.config/clash > /tmp/clash.log 2>&1 &
```


---

## 快速命令总结

```bash
# 安装
wget https://github.com/Dreamacro/clash/releases/download/v1.18.0/clash-linux-amd64-v1.18.0.gz
gunzip clash-linux-amd64-v1.18.0.gz
chmod +x clash-linux-amd64-v1.18.0 && sudo mv clash-linux-amd64-v1.18.0 /usr/local/bin/clash

# 启动
nohup clash -d ~/.config/clash > /tmp/clash.log 2>&1 &

# 停止
pkill clash

# 查看进程
ps aux | grep clash

# 测试代理
curl -x 127.0.0.1:7890 https://www.google.com

# 设置代理
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
```

---

## 相关笔记

- [[主流 VPN 协议指南]] — 协议选型（SS/Vmess/Trojan 等）
- [[Clash Meta 配置指南]] — 核心配置概念
- [[Clash&Mihomo 规则配置完全指南]] — 规则配置详解