
## 核心概念

流量走向：`rules` 匹配 → 指向 `proxy-groups` → proxy-groups 选出具体节点


---

## 一、proxies / proxy-providers

节点来源两种方式：

**直接写节点（proxies）：**

```yaml
proxies:
  - name: "香港1"
    type: ss
    server: 1.2.3.4
    port: 443
    cipher: aes-256-gcm
    password: "xxx"
```

**远程订阅（proxy-providers）：**

```yaml
proxy-providers:
  my_provider:
    type: http
    url: "订阅链接"
    interval: 3600      # 多久刷新一次（秒）
    health-check:
      enable: true
      url: https://cp.cloudflare.com/generate_204
      interval: 300     # 多久测速一次
```


---

## 二、proxy-groups

代理组，就是"选择器"，有几种类型：

| type | 作用 |
|----|----|
| `select` | 手动选，UI 里点 |
| `url-test` | 自动选延迟最低的 |
| `fallback` | 自动按顺序故障转移 |
| `load-balance` | 负载均衡 |

```yaml
- name: 我的代理组
  type: select
  use:
    - my_provider    # 引入 provider 里的所有节点
  proxies:
    - DIRECT         # 也可以加特殊选项或其他组名
    - 另一个组
```

> `proxies` 列表**第一个**就是默认选中的。


---

## 三、rules

从上到下匹配，**先匹配先生效**，最后 `MATCH` 兜底。

常用规则类型：

```yaml
rules:
  - DOMAIN,google.com,代理组名          # 精确域名
  - DOMAIN-SUFFIX,google.com,代理组名   # 匹配子域名
  - DOMAIN-KEYWORD,google,代理组名      # 包含关键词
  - IP-CIDR,192.168.0.0/16,DIRECT      # IP 段
  - GEOIP,CN,DIRECT                    # 地理 IP
  - RULE-SET,规则集名,代理组名           # 引用 rule-providers
  - MATCH,代理组名                      # 兜底，必须最后一条
```

`no-resolve`：加在 IP 类规则后面，不对域名做 DNS 解析直接匹配，避免 DNS 泄漏：

```yaml
- GEOIP,CN,DIRECT,no-resolve
```


---

## 四、rule-providers

把规则列表外包给远程文件管理：

```yaml
rule-providers:
  Google:
    type: http
    behavior: classical   # 规则文件格式
    url: "远程规则文件 url"
    path: ./ruleset/google.yaml
    interval: 86400
```

`behavior` 三种：

| behavior | 内容格式 |
|----|----|
| `classical` | 完整规则，如 `DOMAIN,xxx.com` |
| `domain` | 纯域名列表 |
| `ipcidr` | 纯 IP 段列表 |


---

## 五、DNS

### fake-ip 模式（推荐）

Clash 对所有域名返回假 IP，流量到达时再实际解析，速度快、防 DNS 泄漏。

```yaml
dns:
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:          # 这些域名不使用 fake-ip，直接真实解析
    - '*.lan'
    - '*.local'
  nameserver:              # 走代理的域名用这里解析
    - https://1.1.1.1/dns-query
    - https://8.8.8.8/dns-query
  nameserver-policy:       # 按规则指定 DNS
    "geosite:cn,private":
      - https://doh.pub/dns-query   # 国内域名走国内 DNS
```

### proxy-server-nameserver

专门用于解析代理节点的域名（避免代理节点地址本身走代理解析）：

```yaml
dns:
  proxy-server-nameserver:
    - https://223.5.5.5/dns-query
```


---

## 六、常用特殊值

| 值 | 含义 |
|----|----|
| `DIRECT` | 直连，不走代理 |
| `REJECT` | 拒绝，屏蔽流量 |
| `GLOBAL` | 全局代理组 |


---

## 七、典型结构示例

```yaml
# 1. 订阅节点
proxy-providers:
  my_sub:
    type: http
    url: "..."
    interval: 3600

# 2. 代理组
proxy-groups:
  - name: 手动切换
    type: select
    use: [my_sub]

  - name: 自动选择
    type: url-test
    url: http://www.gstatic.com/generate_204
    interval: 300
    use: [my_sub]

  - name: 漏网之鱼     # 兜底组，第一个是默认
    type: select
    proxies:
      - 手动切换
      - 自动选择
      - DIRECT

# 3. 规则集
rule-providers:
  gfw:
    type: http
    behavior: domain
    url: "..."
    path: ./ruleset/gfw.yaml
    interval: 86400

# 4. 规则
rules:
  - RULE-SET,gfw,手动切换
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,漏网之鱼
```