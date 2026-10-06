---
publish: true
tags:
  - Prometheus
  - Alertmanager
  - ntfy
  - 告警
  - homelab
---
> 日期：2026-10-06
> 背景：Prometheus 告警此前没有任何通知出口（规则未加载、Alertmanager 未启动、receiver 为 null），本次打通"规则 → Alertmanager → ntfy → 手机"整条链路
> 公网入口沿用《阿里云 ECS + FRP + Nginx 公网服务部署 SOP》的架构

---

## 架构

```
Prometheus (rules/*.yml)
↓ 告警
Alertmanager :9093
↓ webhook http://ntfy:80/homelab-alerts?template=am (Bearer token，只写)
ntfy :2586 (docker-host 192.168.31.1)
↑ frp 隧道：ECS 127.0.0.1:6586 → bastion frpc → 192.168.31.1:2586
nginx :443 (阿里云 ECS，HTTPS 终止，ntfy.onecloud.xin)
↑ WebSocket / JSON 长连接
Android ntfy app (phone 账号，只读)
```

**核心原则：**
- ntfy 自建，`deny-all`，所有读写必须带账号或 token
- Alertmanager → ntfy 走 docker 内网，不绕公网
- 手机经公网访问；出门在外也能收到告警
- 推送内容由 ntfy 模板渲染：critical 强提醒、恢复静默

### 关键文件（docker-host `/root/monitoring/`）

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | prometheus / alertmanager / ntfy 等服务 |
| `prometheus.yml` | `alerting` + `rule_files` |
| `rules/node-up.yml` | 告警规则 |
| `alertmanager.yml` | 路由、receiver（含 ntfy token） |
| `ntfy/etc/server.yml` | ntfy 服务端配置 |
| `ntfy/etc/templates/am.yml` | Alertmanager → ntfy 消息模板 |
| `ntfy/lib/user.db` | ntfy 账号、权限、token（**要备份**） |
| `ntfy/cache/cache.db` | 消息缓存（72h） |

---

## 第一步：Prometheus 告警规则

### 1.1 compose 挂载规则目录

```yaml
prometheus:
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - ./rules:/etc/prometheus/rules:ro
    - ./data:/prometheus
```

### 1.2 prometheus.yml

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'rules/*.yml'
```

### 1.3 rules/node-up.yml

```yaml
groups:
  - name: node-up
    interval: 30s
    rules:
      - alert: NodeDown
        expr: up{job="node"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: 'node_exporter down: {{ $labels.instance }}'
          description: '{{ $labels.instance }} 的 node_exporter 已失联超过 2 分钟。'

      # agent / database 是 remote write 推过来的,机器挂了只会停推,
      # 不会出现 up == 0,所以用"数据断了"来判断。
      - alert: RemoteWriteStale
        expr: |
          absent_over_time(up{job="node", instance="agent"}[5m])
          or
          absent_over_time(up{job="node", instance="database"}[5m])
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: 'remote write 中断: {{ $labels.instance }}'
          description: '{{ $labels.instance }} 已超过 5 分钟没有推送指标,机器或 Alloy 可能挂了。'
```

> ⚠️ **`up == 0` 只覆盖 Prometheus 自己抓取的 target**。通过 remote write 推上来的机器（agent、database）挂掉时只是停止推送，`up` 变成 stale 而不是 0，NodeDown 不会触发，必须用 `absent_over_time` 单独兜底。新增 remote write 机器时记得加进 RemoteWriteStale。

### 1.4 校验 & 生效

```bash
docker run --rm -v $PWD/rules:/r:ro --entrypoint promtool prom/prometheus:latest check rules /r/node-up.yml
docker compose up -d prometheus # 改了 compose 挂载必须重建，不是 restart

curl -s localhost:9090/api/v1/rules # 能看到 node-up 组
curl -s localhost:9090/api/v1/alertmanagers # activeAlertmanagers 里有 alertmanager:9093
```

---

## 第二步：部署 ntfy

### 2.1 compose

```yaml
ntfy:
  image: binwiederhier/ntfy:v2.28.0
  container_name: ntfy
  restart: unless-stopped
  command: serve
  ports:
    - '2586:80' # 给 bastion frpc 访问
  volumes:
    - ./ntfy/etc:/etc/ntfy:ro
    - ./ntfy/cache:/var/cache/ntfy
    - ./ntfy/lib:/var/lib/ntfy
  healthcheck:
    test: ["CMD-SHELL", "wget -q --tries=1 http://localhost:80/v1/health -O - | grep -Eo '\"healthy\"\\s*:\\s*true' || exit 1"]
    interval: 60s
    timeout: 10s
    retries: 3
```

### 2.2 ntfy/etc/server.yml

```yaml
base-url: "https://ntfy.onecloud.xin"
listen-http: ":80"
behind-proxy: true

cache-file: "/var/cache/ntfy/cache.db"
cache-duration: "72h"

auth-file: "/var/lib/ntfy/user.db"
auth-default-access: "deny-all"
enable-login: true
enable-signup: false

log-level: info
```

```bash
mkdir -p ntfy/etc/templates ntfy/cache ntfy/lib
docker compose up -d ntfy
curl -s localhost:2586/v1/health # {"healthy":true}
curl -s -o /dev/null -w '%{http_code}\n' -d x localhost:2586/homelab-alerts # 403 = 鉴权生效
```

### 2.3 账号与权限

| 账号 | 权限 | 用途 |
|---|---|---|
| `alertmanager` | `homelab-alerts` write-only | Alertmanager 推送（用 token） |
| `phone` | `homelab-alerts` read-only | 手机订阅（用密码） |

```bash
# Alertmanager 用户（密码随机，反正只用 token）
docker exec -e NTFY_PASSWORD="$(head -c 24 /dev/urandom | base64)" ntfy ntfy user add alertmanager
docker exec ntfy ntfy access alertmanager homelab-alerts write-only
docker exec ntfy ntfy token add --label=alertmanager alertmanager # 记下 tk_xxx

# 手机用户
docker exec -e NTFY_PASSWORD='<手机密码>' ntfy ntfy user add phone
docker exec ntfy ntfy access phone homelab-alerts read-only

docker exec ntfy ntfy user list # 核对
```

> ⚠️ 用 `NTFY_PASSWORD` 环境变量避免交互输入；不要把 token 打到屏幕或写进笔记。

### 2.4 消息模板 ntfy/etc/templates/am.yml

```yaml
# Alertmanager webhook -> ntfy。用法: ?template=am
title: |
  {{- if eq .status "firing" -}}
  [{{ len .alerts }}] {{ .commonLabels.alertname }}{{ with .commonLabels.instance }} @ {{ . }}{{ end }}
  {{- else -}}
  已恢复: {{ .commonLabels.alertname }}{{ with .commonLabels.instance }} @ {{ . }}{{ end }}
  {{- end }}
message: |
  {{- range .alerts }}
  {{ if eq .status "firing" }}🔥{{ else }}✅{{ end }} {{ or .annotations.summary .labels.alertname }}
  {{- with .annotations.description }}
  {{ . }}{{ end }}
  实例: {{ .labels.instance }} 级别: {{ or .labels.severity "-" }}
  开始: {{ .startsAt }}
  {{- if eq .status "resolved" }}
  结束: {{ .endsAt }}{{ end }}
  {{ end }}
priority: |
  {{- if and (eq .status "firing") (eq .commonLabels.severity "critical") }}5{{ else if eq .status "firing" }}4{{ else }}2{{ end -}}
```

| 情况 | 优先级 | 手机表现 |
|---|---|---|
| firing + critical | 5 (urgent) | 强提醒、响铃 |
| firing 其他级别 | 4 (high) | 普通提醒 |
| resolved | 2 (low) | 静默 |

> ⚠️ **不要用 ntfy 内置的 `?template=alertmanager`**：它只渲染 title/message，**会吞掉 priority**（URL 参数和 `X-Priority` 头都无效），所有告警都变成默认优先级。自定义模板里写 `priority:` 才生效。
> 模板改完要 `docker restart ntfy` 重新加载。时间是 UTC（北京时间 -8h）。

---

## 第三步：Alertmanager 接 ntfy

### 3.1 alertmanager.yml

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'ntfy'

receivers:
  - name: 'null'
  - name: 'ntfy'
    webhook_configs:
      - url: 'http://ntfy:80/homelab-alerts?template=am'
        send_resolved: true
        http_config:
          authorization:
            type: Bearer
            credentials: '<ALERTMANAGER_TOKEN>'
  - name: 'queen-webhook'
    webhook_configs:
      - url: 'http://192.168.31.3:9099/alert'
        send_resolved: true

inhibit_rules: []
```

> token 放 `http_config.authorization`，**不要拼进 URL**（URL 会出现在日志里）。

### 3.2 校验 & 热加载（不用重启）

```bash
docker exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
curl -XPOST localhost:9093/-/reload
docker logs alertmanager --since 1m | grep -i 'Completed loading'

# 发送统计：sent 增长、failed 为 0
curl -s localhost:9093/metrics | grep -E 'alertmanager_notifications(_failed)?_total\{.*webhook'
```

### 3.3 以后接 queen 桥（同时发两边）

```yaml
route:
  receiver: 'ntfy'
  routes:
    - receiver: 'queen-webhook'
      continue: true # 匹配后继续走默认 ntfy
```

---

## 第四步：公网入口（ECS）

按《阿里云 ECS + FRP + Nginx 公网服务部署 SOP》的"后续加服务流程"走一遍。

### 4.1 DNS

| 域名 | 记录类型 | 值 |
|---|---|---|
| ntfy.onecloud.xin | A | <ECS 公网 IP> |

### 4.2 证书（acme.sh + 阿里云 DNS）

```bash
~/.acme.sh/acme.sh --issue -d ntfy.onecloud.xin --dns dns_ali --dnssleep 60 \
  && ~/.acme.sh/acme.sh --install-cert -d ntfy.onecloud.xin --ecc \
  --cert-file /etc/nginx/ssl/ntfy.onecloud.xin/cert.pem \
  --key-file /etc/nginx/ssl/ntfy.onecloud.xin/privkey.pem \
  --fullchain-file /etc/nginx/ssl/ntfy.onecloud.xin/fullchain.pem \
  --reloadcmd "systemctl reload nginx" \
  && chmod 600 /etc/nginx/ssl/ntfy.onecloud.xin/privkey.pem
```

> ⚠️ **必须加 `--dnssleep 60`**：acme.sh 默认用 Cloudflare/Google DoH 检查 TXT 记录，国内 ECS 连不上，报 `error code: 35` 然后卡死。
> ⚠️ **申请过程中不要 Ctrl+C**：中断会留下 `_acme-challenge` TXT 记录，下次重试复用同一个值，阿里云报 `The DNS record already exists`。处理：到阿里云 DNS 控制台手动删掉 `_acme-challenge.<子域>` 的 TXT 记录再重试。
> 用 `&&` 串起来，issue 失败就不会去 install。

### 4.3 nginx：/etc/nginx/conf.d/ntfy.onecloud.xin.conf

```nginx
# ntfy: 手机 -> nginx:443 -> frps 127.0.0.1:6586 -> bastion frpc -> docker-host 192.168.31.1:2586

map $http_upgrade $ntfy_connection {
    default upgrade;
    '' '';
}

server {
    listen 443 ssl;
    server_name ntfy.onecloud.xin;

    ssl_certificate /etc/nginx/ssl/ntfy.onecloud.xin/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/ntfy.onecloud.xin/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:6586;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket / 长连接(Android 即时推送依赖这些)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $ntfy_connection;

        # 流式推送不能缓冲,超时要大于 ntfy keepalive(45s)
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;
        proxy_read_timeout 3m;
        proxy_send_timeout 3m;
    }
}

server {
    listen 80;
    server_name ntfy.onecloud.xin;
    return 301 https://$host$request_uri;
}
```

```bash
nginx -t && systemctl reload nginx
```

> ⚠️ 和普通网站反代的区别就在 `location` 后半段：**`proxy_buffering off` + 超时 > 45s + WebSocket 头**。少了任何一个，手机即时推送都会频繁断线或延迟。
> ⚠️ 证书文件不存在时 `nginx -t` 直接失败，**会拖累所有站点 reload**。证书没到位前先把 conf 改名 `.conf.off`。

### 4.4 frpc（bastion `/root/frp/frpc.toml`）

```toml
[[proxies]]
name = "ntfy"
type = "tcp"
localIP = "192.168.31.1"
localPort = 2586
remotePort = 6586
```

```bash
systemctl restart frpc
```

> 6586 不要在安全组放行，只给本机 nginx 用。

---

## 第五步：手机（Android）

1. 安装 ntfy app
2. 设置 → 添加服务器 `https://ntfy.onecloud.xin`，登录 `phone` 账号
3. 订阅 topic `homelab-alerts`
4. 订阅设置里打开 **Instant delivery**
5. 系统设置里给 ntfy **关闭电池优化 / 允许后台运行 / 允许自启**（国产 ROM 必做，否则后台被杀收不到）

> Android 自建服务器直接长连接，**不需要** `upstream-base-url`；那个只有 iOS 才需要（借 ntfy.sh 唤醒）。

---

## 第六步：测试链路

### 6.1 ECS

```bash
ss -tlnp | grep 6586
curl -s http://127.0.0.1:6586/v1/health # frp 隧道
curl -s https://ntfy.onecloud.xin/v1/health # 整条链路
```

### 6.2 docker-host：经公网发一条测试告警

```bash
AT=$(grep -oE 'tk_[a-z0-9]+' /root/monitoring/alertmanager.yml)
curl -s -H "Authorization: Bearer $AT" "https://ntfy.onecloud.xin/homelab-alerts?template=am" \
  -d '{"status":"firing","receiver":"ntfy","commonLabels":{"alertname":"E2ETest","severity":"warning","instance":"test"},
  "alerts":[{"status":"firing","labels":{"alertname":"E2ETest","instance":"test","severity":"warning"},
  "annotations":{"summary":"链路测试,可忽略"},"startsAt":"2026-01-01T00:00:00Z"}]}'
```

手机应立即收到 `[1] E2ETest @ test`。

### 6.3 鉴权检查

```bash
curl -s -o /dev/null -w '%{http_code}\n' -d x https://ntfy.onecloud.xin/homelab-alerts # 403
curl -s -o /dev/null -w '%{http_code}\n' https://ntfy.onecloud.xin/homelab-alerts/json?poll=1 # 403
curl -s -o /dev/null -w '%{http_code}\n' http://ntfy.onecloud.xin/ # 301
```

### 6.4 长连接检查（可选）

临时给 phone 发一个 10 分钟 token，订阅 70 秒，应看到 `open` → `keepalive`（约 45s）→ 不断线：

```bash
RT=$(docker exec ntfy ntfy token add --expires=10m phone | grep -oE 'tk_[a-z0-9]+')
curl -sN -m 70 -H "Authorization: Bearer $RT" https://ntfy.onecloud.xin/homelab-alerts/json
docker exec ntfy ntfy token remove phone $RT
```

---

## 日常运维

| 操作 | 命令 |
|---|---|
| 改规则 | 编辑 `rules/*.yml` → promtool 校验 → `docker restart prometheus`（未开 lifecycle） |
| 改路由 | 编辑 `alertmanager.yml` → amtool 校验 → `curl -XPOST localhost:9093/-/reload` |
| 改模板 | 编辑 `ntfy/etc/templates/am.yml` → `docker restart ntfy` |
| 查当前告警 | `curl -s localhost:9090/api/v1/alerts` / `curl -s localhost:9093/api/v2/alerts` |
| 临时静默 | Alertmanager UI `:9093` → Silences |
| 轮换 AM token | `ntfy token add` 新的 → 改 alertmanager.yml → reload → `ntfy token remove alertmanager <旧>` |
| 加手机/设备 | `ntfy user add` + `ntfy access <user> homelab-alerts read-only` |
| 备份 | `ntfy/lib/user.db`（账号）、`alertmanager.yml`、`rules/` |

---

## 排障清单

| 症状 | 可能原因 | 排查方法 |
|---|---|---|
| `/api/v1/rules` 返回空 | rules 目录没挂进容器 / 改 compose 后没重建 | `docker exec prometheus ls /etc/prometheus/rules`；`docker compose up -d prometheus` |
| `activeAlertmanagers: []` | Prometheus 没重新加载配置 / alertmanager 容器不存在 | `docker ps`；容器名必须是 compose 里的 `alertmanager` |
| 有 alertmanager 容器但连不上 | 手动 `docker run` 起的，在 `bridge` 网络，没挂配置 | 删掉，只用 `docker compose up -d alertmanager` |
| 机器挂了没告警 | remote write 机器 `up` 不会变 0 | 用 `absent_over_time` 规则（RemoteWriteStale） |
| AM 收到告警但手机没收到 | receiver 还是 `null` / token 错 | `amtool` 看路由；metrics 里 `notifications_failed_total`；`docker logs alertmanager` |
| 推送是一大坨 JSON | URL 少了 `?template=am` | 检查 webhook url |
| 所有告警优先级都一样 | 用了内置 `alertmanager` 模板 | 换成自定义 `am` 模板 |
| 手机在家能收、出门收不到 | 域名解析到内网 IP | 公网 DNS 查 `1.1.1.1` 确认解析到 ECS IP |
| 手机推送延迟 / 频繁重连 | nginx 缓冲或超时 | 检查 `proxy_buffering off`、`proxy_read_timeout 3m`、Upgrade 头 |
| 手机锁屏后收不到 | 电池优化杀后台 | 关电池优化、允许自启、开 Instant delivery |
| acme.sh 卡在 DNS 检查 `error code: 35` | 国内连不上 DoH | 加 `--dnssleep 60` |
| acme.sh `The DNS record already exists` | 上次中断残留 TXT | 阿里云控制台删 `_acme-challenge.<子域>` |
| `install-cert` 报 `.cer: No such file` | issue 没成功 | 先确认 issue 输出 `Cert success.` |

---

## 安全要点

1. **ntfy `deny-all` + 关闭注册**——匿名读写全部 403
2. **最小权限**——Alertmanager 只写、手机只读，各自独立账号
3. **token 不进 URL、不进笔记**——AM 用 `http_config.authorization`；本文档只写占位符
4. **frps 隧道端口不放行**——6586 只给本机 nginx 用
5. **证书私钥 `chmod 600`**
6. **`ntfy/lib/user.db` 含账号哈希和 token**——备份时注意存放位置

---

## 后续 TODO

- [ ] queen 桥上线后加子路由（`continue: true`），确认地址是 31.3 还是 31.101
- [x] 模板时间改为北京时间 ✅ 2026-10-07
- [x] 更多规则：磁盘、内存、CPU、证书到期、Loki 日志告警 ✅ 2026-10-07
- [x] 监控 ntfy 自身（`/v1/health` 用 blackbox_exporter 探测）——否则 ntfy 挂了告警会静默丢失 ✅ 2026-10-07
- [x] Prometheus/Alertmanager 镜像固定版本，不用 `latest` ✅ 2026-10-07
