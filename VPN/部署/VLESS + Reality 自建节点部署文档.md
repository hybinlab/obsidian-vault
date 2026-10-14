---
tags:
  - 部署
---
# VLESS + Reality 自建节点部署文档

> 环境：搬瓦工 VPS / Ubuntu 24.04 / 3X-UI 面板

---
## 一、安装 3X-UI 面板

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

安装过程选项：
- 数据库：SQLite
- 面板端口：自定义（记录好）
- SSL 证书：选 **2（Let's Encrypt for IP Address）**

> 若 80 端口被 nginx 占用导致证书申请失败，先 `systemctl stop nginx`，再进面板菜单选 **19 → 6** 重新申请。

申请成功后重启 nginx：

```bash
systemctl start nginx
```

---

## 二、访问面板

```
https://<你的VPS IP>:<面板端口>/<WebBasePath>/
```

初始账号密码在安装日志末尾，妥善保存。

---

## 三、创建 VLESS+Reality 入站

进入面板 → **入站** → **添加入站**，按以下配置填写：

### 基础配置
| 项目 | 值 |
|------|-----|
| 协议 | vless |
| 端口 | 443 |

### 传输
| 项目 | 值 |
|------|-----|
| 传输 | RAW（TCP） |

### 安全
| 项目 | 值 |
|------|-----|
| 安全 | Reality |
| uTLS | chrome |
| 目标 | microsoft.com:443 |
| SNI | microsoft.com |
| 公私钥 | 点"获取新证书"自动生成 |

点**创建**保存。

---

## 四、添加用户

进入面板 → **客户端** → **添加客户端**：

| 项目 | 值 |
|------|-----|
| 关联入站 | 选择刚创建的入站 |
| 流动 | xtls-rprx-vision |
| UUID | 自动生成 |

点**创建**保存。

---

## 五、导出节点链接

入站列表 → 点对应入站的**导出**图标 → 复制 `vless://` 开头的链接。

---

## 六、导入到 PassWall

PassWall → **节点列表** → **通过链接添加节点** → 粘贴链接 → 添加。

---

## 七、放行防火墙端口

```bash
iptables -I INPUT -p tcp --dport 443 -j ACCEPT
```

验证：

```bash
iptables -L INPUT -n
```

确认有 `tcp dpt:443 ACCEPT` 即可。

---

## 八、注意事项

- SSL 证书有效期 **6 天**，acme.sh 会自动续期，无需手动操作
- 节点协议为 Xray 内核，PassWall 过滤模式保持 **Xray**
- 搬瓦工后台无防火墙管理界面，端口管理在系统内用 iptables 操作
- 推荐定期执行 `x-ui update` 保持面板版本最新
