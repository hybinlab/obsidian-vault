
### 📖 目录


1. [基础概念](#%E5%9F%BA%E7%A1%80%E6%A6%82%E5%BF%B5)
2. [规则语法](#%E8%A7%84%E5%88%99%E8%AF%AD%E6%B3%95)
3. [匹配类型详解](#%E5%8C%B9%E9%85%8D%E7%B1%BB%E5%9E%8B%E8%AF%A6%E8%A7%A3)
4. [实战例子](#%E5%AE%9E%E6%88%98%E4%BE%8B%E5%AD%90)
5. [规则优先级](#%E8%A7%84%E5%88%99%E4%BC%98%E5%85%88%E7%BA%A7)
6. [常见错误](#%E5%B8%B8%E8%A7%81%E9%94%99%E8%AF%AF)
7. [调试方法](#%E8%B0%83%E8%AF%95%E6%96%B9%E6%B3%95)
8. [完整配置模板](#%E5%AE%8C%E6%95%B4%E9%85%8D%E7%BD%AE%E6%A8%A1%E6%9D%BF)


### 基础概念

Clash 是一个网络代理工具，**规则（Rule）** 决定了哪些网站流量走代理，哪些直连。

**核心思想：**

* 国内网站 → 直连（DIRECT）✅ 快速
* 国外网站 → 代理（通过代理组） 🌍 翻墙
* 本地网络 → 直连（DIRECT） 🏠 内网访问


---

### 规则语法

#### 基本格式

```
- [匹配类型],[匹配值],[代理组/行为]
```

**组成部分：**

* **匹配类型**：如何识别网站（DOMAIN、DOMAIN-SUFFIX 等）
* **匹配值**：要匹配的具体内容（google.com、\*.twitter.com 等）
* **代理组/行为**：DIRECT（直连）或代理组名称（国外流量、AI服务等）

#### 例子

```yaml
- DOMAIN-SUFFIX,google.com,国外流量      # google 的所有子域都走代理
- IP-CIDR,192.168.0.0/16,DIRECT          # 局域网直连
- GEOIP,cn,DIRECT                        # 国内 IP 直连
- MATCH,国外流量                         # 兜底规则：其他都走代理
```


---

### 匹配类型详解

| 类型 | 用途 | 例子 | 匹配范围 |
|----|----|----|----|
| **DOMAIN** | 精确匹配域名 | `DOMAIN,google.com` | 仅 google.com |
| **DOMAIN-SUFFIX** | 匹配域名后缀 ⭐⭐⭐ | `DOMAIN-SUFFIX,google.com` | google.com、www.google.com、api.google.com |
| **DOMAIN-KEYWORD** | 匹配域名关键字 | `DOMAIN-KEYWORD,google` | google.com、mygoogle.com、google.cn |
| **IP-CIDR** | 匹配 IP 段 | `IP-CIDR,192.168.0.0/16,no-resolve` | 192.168.x.x 的所有 IP |
| **GEOIP** | 地理位置（按 IP） | `GEOIP,cn` | 国内的 IP 地址 |
| **GEOSITE** | 地理位置（按域名） | `GEOSITE,cn` | 国内的网站域名 |
| **MATCH** | 兜底规则 | `MATCH,国外流量` | 前面都不匹配的流量 |

#### 各类型详解

##### 1️⃣ DOMAIN-SUFFIX（最常用）

* **作用**：匹配域名的后缀
* **场景**：99% 的场景都用这个
* **例子**：

  ```yaml
  - DOMAIN-SUFFIX,google.com,国外流量      # 匹配：google.com、www.google.com、mail.google.com
  - DOMAIN-SUFFIX,github.com,开发工具      # 匹配：github.com、api.github.com
  ```

##### 2️⃣ DOMAIN

* **作用**：精确匹配整个域名
* **场景**：需要精确控制时
* **例子**：

  ```yaml
  - DOMAIN,google.com,国外流量            # 只匹配 google.com，不匹配 www.google.com
  ```

##### 3️⃣ DOMAIN-KEYWORD

* **作用**：匹配域名中包含的关键字
* **场景**：一个公司有多个域名
* **例子**：

  ```yaml
  - DOMAIN-KEYWORD,twitter,国外流量       # 匹配：twitter.com、t.co、twimg.com（不行）等含 twitter 的域名
  - DOMAIN-KEYWORD,anthropic,AI服务       # 匹配：anthropic.com、api.anthropic.com
  ```

##### 4️⃣ IP-CIDR

* **作用**：匹配 IP 地址段
* **场景**：处理 IP 级别的流量
* **例子**：

  ```yaml
  - IP-CIDR,127.0.0.1/8,DIRECT            # 本地 IP (127.0.0.x)
  - IP-CIDR,192.168.0.0/16,DIRECT         # 局域网 (192.168.x.x)
  - IP-CIDR,10.0.0.0/8,DIRECT             # 内网 (10.x.x.x)
  ```
* **参数说明**：
  * `no-resolve`：不进行 DNS 解析（推荐加上，性能更好）
  * 例：`IP-CIDR,192.168.0.0/16,DIRECT,no-resolve`

##### 5️⃣ GEOSITE / GEOIP

* **作用**：基于地理位置（国家）的规则
* **原理**：Clash 内置地理库，根据 IP/域名 判断所属国家
* **例子**：

  ```yaml
  - GEOSITE,cn,DIRECT                     # 国内网站直连
  - GEOIP,cn,DIRECT                       # 国内 IP 直连
  ```
* **常用国家代码**：
  * `cn` - 中国
  * `us` - 美国
  * `jp` - 日本
  * `sg` - 新加坡

##### 6️⃣ MATCH（兜底规则）

* **作用**：前面都不匹配就用这个
* **位置**：必须放在最后
* **例子**：

  ```yaml
  - MATCH,国外流量                        # 其他所有流量走代理
  ```


---

### 实战例子

#### 场景 1：配置推特（Twitter）

```yaml
# 推特主域名
- DOMAIN-SUFFIX,twitter.com,国外流量

# 推特的短链和图片服务
- DOMAIN-SUFFIX,t.co,国外流量
- DOMAIN-SUFFIX,twimg.com,国外流量

# 或者用关键字一次搞定（但不够精确）
- DOMAIN-KEYWORD,twitter,国外流量
```

#### 场景 2：配置 AI 服务

```yaml
# OpenAI
- DOMAIN-SUFFIX,openai.com,AI服务
- DOMAIN-SUFFIX,api.openai.com,AI服务
- DOMAIN-KEYWORD,chatgpt,AI服务

# Anthropic (Claude)
- DOMAIN-SUFFIX,anthropic.com,AI服务
- DOMAIN-KEYWORD,claude,AI服务

# Google AI
- DOMAIN-SUFFIX,google.com,AI服务
- DOMAIN-SUFFIX,googleapis.com,AI服务
```

#### 场景 3：配置开发工具

```yaml
# GitHub
- DOMAIN-SUFFIX,github.com,开发工具
- DOMAIN-SUFFIX,githubusercontent.com,开发工具

# Docker
- DOMAIN-SUFFIX,docker.com,开发工具
- DOMAIN-SUFFIX,dockerhub.com,开发工具

# Stack Overflow
- DOMAIN-SUFFIX,stackoverflow.com,开发工具
```

#### 场景 4：本地网络

```yaml
# 本地 loopback
- DOMAIN-SUFFIX,localhost,DIRECT
- DOMAIN-SUFFIX,local,DIRECT
- IP-CIDR,127.0.0.1/8,DIRECT,no-resolve

# 局域网
- IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
- IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
- IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
```


---

### 规则优先级

#### 执行顺序（从上到下）

```yaml
rules:
  # 第1层：本地/内网（必须最先）
  - IP-CIDR,127.0.0.1/8,DIRECT
  - IP-CIDR,192.168.0.0/16,DIRECT

  # 第2层：具体服务（越具体越靠前）
  - DOMAIN-SUFFIX,anthropic.com,AI服务
  - DOMAIN-SUFFIX,openai.com,AI服务

  # 第3层：国家级规则（通用规则）
  - GEOSITE,cn,DIRECT
  - GEOIP,cn,DIRECT

  # 第4层：兜底规则（必须最后）
  - MATCH,国外流量
```

#### 核心原则

**具体 → 通用，从上到下**

```
❌ 错误：通用规则写前面，后面的永远用不上
- MATCH,国外流量                    # ← 这会匹配所有，后面的都用不上
- DOMAIN-SUFFIX,google.com,代理    # ← 永远无法执行

✅ 正确：具体规则优先
- DOMAIN-SUFFIX,google.com,代理    # ← 先处理具体的
- MATCH,国外流量                    # ← 再兜底
```


---

### 常见错误

#### ❌ 错误 1：域名写错

```yaml
# 错误：typo
- DOMAIN-SUFFIX,googlr.com,国外流量      # ❌ "googlr" 拼写错误

# 正确
- DOMAIN-SUFFIX,google.com,国外流量      # ✅
```

#### ❌ 错误 2：代理组名不存在

```yaml
rules:
  - DOMAIN-SUFFIX,google.com,不存在的组  # ❌ "不存在的组" 在 proxy-groups 里没定义

proxy-groups:
  - name: 国外流量
    type: select
    proxies:
      - xxx
```

**解决：检查 proxy-groups 中是否有对应名称**

#### ❌ 错误 3：兜底规则不在最后

```yaml
rules:
  - MATCH,国外流量                       # ❌ 写在前面
  - DOMAIN-SUFFIX,google.com,代理       # 永远无法执行
```

#### ❌ 错误 4：混淆 DIRECT 和代理组名

```yaml
# 错误：DIRECT 是行为，不是代理组名
- DOMAIN-SUFFIX,google.com,直连         # ❌ "直连" 是中文描述，不能这样写

# 正确：用 DIRECT 关键字或代理组名
- DOMAIN-SUFFIX,google.com,DIRECT       # ✅ 关键字
- DOMAIN-SUFFIX,google.com,国外流量     # ✅ 代理组名
```

#### ❌ 错误 5：YAML 缩进不对

```yaml
# 错误：缩进混乱
rules:
- DOMAIN-SUFFIX,google.com,国外流量       # ❌ 没缩进
 - DOMAIN-SUFFIX,github.com,开发工具      # ❌ 缩进只有1格
  - DOMAIN-SUFFIX,twitter.com,国外流量    # ❌ 缩进是2格但前面的是0格

# 正确：统一用 2 格缩进
rules:
  - DOMAIN-SUFFIX,google.com,国外流量
  - DOMAIN-SUFFIX,github.com,开发工具
  - DOMAIN-SUFFIX,twitter.com,国外流量
```


---

### 调试方法

#### 1️⃣ 问题：网站不走代理（应该走但没走）

**步骤：**


1. 打开 **F12 开发者工具** → **Network 标签**
2. 刷新网页，找到该网站的请求
3. 查看 **请求的域名**（如 `api.example.com`）
4. 在规则中添加：

   ```yaml
   - DOMAIN-SUFFIX,example.com,国外流量
   ```
5. **重启代理工具**
6. 刷新网页，检查是否走代理

#### 2️⃣ 问题：网站走代理但不应该走（应该直连但走了）

**步骤：**


1. 同样找到域名
2. 添加直连规则：

   ```yaml
   - DOMAIN-SUFFIX,example.com,DIRECT
   ```
3. **放在其他规则的前面**
4. 重启并测试

#### 3️⃣ 验证规则是否生效

**方法 A：查看日志**

* 大多数代理工具都有日志功能
* 可以看到每个请求匹配了哪条规则

**方法 B：命令行测试（DNS 查询）**

```bash
# Linux/Mac
nslookup google.com

# Windows
nslookup google.com
```

#### 4️⃣ 规则语法验证

* 使用 Clash 配置验证工具
* 或在代理工具的「规则」页面查看是否报错


---

### 完整配置模板

```yaml
port: 7890
socks-port: 7891
mixed-port: 7892
mode: rule
log-level: info

proxies:
  # 这里添加你的代理节点
  - name: "代理1"
    type: ss
    server: 1.2.3.4
    port: 8388
    cipher: 2022-blake3-aes-128-gcm
    password: "your_password"

proxy-groups:
  # 手动选择代理
  - name: "国外流量"
    type: select
    proxies:
      - "代理1"
      - DIRECT

  # AI 服务代理
  - name: "AI服务"
    type: select
    proxies:
      - "代理1"
      - DIRECT

  # 开发工具代理
  - name: "开发工具"
    type: select
    proxies:
      - "代理1"
      - DIRECT

rules:
  # 第1层：本地/内网（最高优先级）
  - DOMAIN-SUFFIX,localhost,DIRECT
  - DOMAIN-SUFFIX,local,DIRECT
  - IP-CIDR,127.0.0.1/8,DIRECT,no-resolve
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve

  # 第2层：AI 服务
  - DOMAIN-SUFFIX,anthropic.com,AI服务
  - DOMAIN-KEYWORD,claude,AI服务
  - DOMAIN-SUFFIX,openai.com,AI服务
  - DOMAIN-KEYWORD,chatgpt,AI服务
  - DOMAIN-SUFFIX,google.com,AI服务
  - DOMAIN-SUFFIX,googleapis.com,AI服务

  # 第3层：开发工具
  - DOMAIN-SUFFIX,github.com,开发工具
  - DOMAIN-SUFFIX,githubusercontent.com,开发工具
  - DOMAIN-SUFFIX,docker.com,开发工具
  - DOMAIN-SUFFIX,stackoverflow.com,开发工具

  # 第4层：社交媒体
  - DOMAIN-SUFFIX,twitter.com,国外流量
  - DOMAIN-SUFFIX,t.co,国外流量
  - DOMAIN-SUFFIX,twimg.com,国外流量
  - DOMAIN-SUFFIX,facebook.com,国外流量
  - DOMAIN-SUFFIX,instagram.com,国外流量

  # 第5层：其他常见国外服务
  - DOMAIN-SUFFIX,youtube.com,国外流量
  - DOMAIN-SUFFIX,amazonaws.com,国外流量
  - DOMAIN-SUFFIX,cloudflare.com,国外流量

  # 第6层：国内网站直连
  - GEOSITE,cn,DIRECT
  - GEOIP,cn,DIRECT

  # 第7层：兜底规则（最低优先级）
  - MATCH,国外流量
```


---

### 快速参考表

#### 快速添加规则

| 场景 | 规则 |
|----|----|
| 网站 example.com 走代理 | `- DOMAIN-SUFFIX,example.com,国外流量` |
| 网站 example.com 直连 | `- DOMAIN-SUFFIX,example.com,DIRECT` |
| 所有含 "example" 的域名走代理 | `- DOMAIN-KEYWORD,example,国外流量` |
| 本地 IP 直连 | `- IP-CIDR,127.0.0.1/8,DIRECT,no-resolve` |
| 局域网直连 | `- IP-CIDR,192.168.0.0/16,DIRECT,no-resolve` |
| 所有国内网站直连 | `- GEOSITE,cn,DIRECT` |
| 所有国外网站走代理 | `- MATCH,国外流量` |


---

### 总结

✅ **要点总结：**


1. **基础语法**：`匹配类型,匹配值,代理组/行为`
2. **最常用**：DOMAIN-SUFFIX（覆盖 99% 的场景）
3. **优先级**：具体 → 通用，从上到下
4. **调试**：用 F12 开发者工具找出域名，然后添加规则
5. **验证**：重启代理工具，刷新网页看是否生效

🚀 **下次遇到网站访问问题，就按这个流程走：**


1. F12 → Network 找到域名
2. 添加 `DOMAIN-SUFFIX` 规则
3. 重启代理
4. 搞定！


---

更新时间：2026-03-13