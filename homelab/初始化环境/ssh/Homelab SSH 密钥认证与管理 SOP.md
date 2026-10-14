### 1. 目标

统一 Homelab SSH 认证方式，避免长期使用密码登录。

设计原则：

- Mac 作为人工管理端，拥有独立 SSH 身份。
- Agent VM 等自动化主体拥有独立 SSH 身份。
- 私钥永远保留在密钥所属设备。
- 服务器只保存公钥。
- 新 VM 优先通过 Cloud-Init 注入公钥。
- 已存在的 VM 使用 `ssh-copy-id` 完成首次公钥部署。
- 不同身份之间禁止共享私钥。

---

### 2. 密钥模型

```text
Mac
├── ~/.ssh/homelab_mac          # 私钥
└── ~/.ssh/homelab_mac.pub      # 公钥
          │
          ├──→ PVE
          ├──→ Docker-Host
          ├──→ Agent
          └──→ 其他 Homelab VM


Agent VM
├── ~/.ssh/homelab_agent        # Agent 私钥
└── ~/.ssh/homelab_agent.pub    # Agent 公钥
          │
          └──→ Agent 确实需要管理的服务器
```

身份划分：

```text
homelab_mac      = 人工管理员身份
homelab_agent    = Agent / 自动化身份
```

禁止：

```text
Mac 与 Agent 共用同一私钥
Agent 获取 Mac 私钥
服务器之间随意复制私钥
私钥提交到 Git
私钥写入 VM Template / Cloud-Init
```

---

## 3. Mac 创建 Homelab 管理密钥

推荐使用 Ed25519：

```bash
ssh-keygen -t ed25519 -a 100 \
  -f ~/.ssh/homelab_mac \
  -C "hyb@homelab"
```

生成：

```text
~/.ssh/homelab_mac
~/.ssh/homelab_mac.pub
```

其中：

```text
homelab_mac       私钥，禁止泄露
homelab_mac.pub   公钥，可以分发
```

---

### 4. 设置本地权限

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/homelab_mac
chmod 644 ~/.ssh/homelab_mac.pub
chmod 600 ~/.ssh/config
```

检查：

```bash
ls -la ~/.ssh
```

私钥建议：

```text
-rw------- homelab_mac
```

公钥：

```text
-rw-r--r-- homelab_mac.pub
```

---

## 5. 已存在服务器首次部署公钥

例如 Agent VM：

```text
192.168.31.4
```

执行：

```bash
ssh-copy-id \
  -i ~/.ssh/homelab_mac.pub \
  root@192.168.31.4
```

第一次需要输入服务器密码。

成功应出现：

```text
Number of key(s) added: 1
```

本质上相当于把：

```text
~/.ssh/homelab_mac.pub
```

添加至远程服务器：

```text
/root/.ssh/authorized_keys
```

---

## 6. 配置 SSH Config

编辑：

```bash
nano ~/.ssh/config
```

示例：

```sshconfig
Host aliyun
  HostName ECS_PUBLIC_IP
  User root
  IdentityFile ~/.ssh/aliyun.pem
  IdentitiesOnly yes

Host agent
  HostName 192.168.31.4
  User root
  IdentityFile ~/.ssh/homelab_mac
  IdentitiesOnly yes

Host docker
  HostName 192.168.31.9
  User root
  IdentityFile ~/.ssh/homelab_mac
  IdentitiesOnly yes

Host database
  HostName 192.168.31.8
  User root
  IdentityFile ~/.ssh/homelab_mac
  IdentitiesOnly yes
```

注意：

```sshconfig
IdentityFile ~/.ssh/homelab_mac
```

	必须指向**私钥**。

错误：

```sshconfig
IdentityFile ~/.ssh/homelab_mac.pub
```

`.pub` 是公钥，不能作为客户端认证私钥使用。

---

## 7. 日常连接

之后不需要记 IP：

```bash
ssh agent
ssh docker
ssh database
```

同样适用于：

```bash
scp file.txt agent:/root/
```

以及：

```bash
rsync -av ./project/ agent:/opt/project/
```

VS Code Remote SSH 同样可以直接使用 SSH Config 中的 Host。

---

## 8. 验证公钥认证

执行：

```bash
ssh agent
```

如果不再要求：

```text
root@192.168.31.4's password:
```

说明公钥认证正常。

需要排查时：

```bash
ssh -vvv agent
```

重点检查：

```text
Offering public key
Server accepts key
Authenticated to ...
```

---

## 9. Agent VM 创建独立密钥

登录 Agent：

```bash
ssh agent
```

生成 Agent 专属密钥：

```bash
ssh-keygen -t ed25519 -a 100 \
  -f ~/.ssh/homelab_agent \
  -C "agent@homelab"
```

得到：

```text
~/.ssh/homelab_agent
~/.ssh/homelab_agent.pub
```

Agent 需要访问其他服务器时，只分发：

```text
homelab_agent.pub
```

禁止将 Mac 的：

```text
homelab_mac
```

复制给 Agent。

---

## 10. Agent 权限控制

遵循最小权限原则。

如果 Agent 只需要管理：

```text
Docker-Host
```

那么只把：

```text
homelab_agent.pub
```

部署到 Docker-Host。

不要默认：

```text
Agent → root → 所有 Homelab 主机
```

尤其 Agent 具备 Shell / Tool Calling 能力时，其 SSH 私钥代表 Agent 能够访问的基础设施范围。

---

## 11. 新 VM 推荐流程

已有 VM 可以使用：

```text
密码登录
    ↓
ssh-copy-id
    ↓
公钥认证
```

但新 VM 不建议长期采用这种方式。

推荐：

```text
PVE
 ↓
创建 Cloud-Init VM
 ↓
Cloud-Init 注入 homelab_mac.pub
 ↓
首次启动
 ↓
authorized_keys 自动生成
 ↓
Mac 直接 SSH 登录
 ↓
Ansible 接管后续配置
```

Cloud-Init 中只允许注入：

```text
homelab_mac.pub
```

禁止注入：

```text
homelab_mac
```

---

## 12. 自动化演进

当前阶段：

```text
Mac
 ↓
ssh-copy-id
 ↓
VM
```

下一阶段：

```text
PVE Template
     +
Cloud-Init
     ↓
自动创建 VM
     ↓
自动注入 SSH Public Key
     ↓
Ansible
     ↓
系统初始化
```

进一步可以演进为：

```text
Terraform
    ↓
PVE API
    ↓
创建 VM
    ↓
Cloud-Init
    ↓
注入 SSH Public Key
    ↓
Ansible
    ↓
配置系统
    ↓
部署服务
```

目标是：

> VM 本身可以随时销毁和重建，真正需要长期保存的是配置、凭据和数据。

---

## 13. 私钥备份

需要备份：

```text
~/.ssh/homelab_mac
```

推荐：

```text
Mac
 ↓
加密备份
 ↓
可靠的离线/受保护存储
```

禁止：

```text
GitHub
GitLab 公共仓库
普通网盘明文
聊天软件
VM Template
Docker Image
```

公钥：

```text
homelab_mac.pub
```

不属于秘密信息。

---

## 14. Mac 丢失或私钥泄漏

如果：

```text
homelab_mac
```

可能已经泄漏，不要继续使用。

生成新密钥：

```bash
ssh-keygen -t ed25519 -a 100 \
  -f ~/.ssh/homelab_mac_new \
  -C "hyb@homelab"
```

将：

```text
homelab_mac_new.pub
```

部署至所有服务器。

确认新密钥可以登录后，从所有：

```text
~/.ssh/authorized_keys
```

删除旧：

```text
homelab_mac.pub
```

最后销毁旧私钥。

---

## 15. 推荐最终结构

Mac：

```text
~/.ssh/
├── config
├── homelab_mac
├── homelab_mac.pub
├── aliyun.pem
└── known_hosts
```

Agent：

```text
/root/.ssh/
├── authorized_keys
├── homelab_agent
├── homelab_agent.pub
└── known_hosts
```

服务器：

```text
/root/.ssh/
└── authorized_keys
    ├── Mac 管理公钥
    └── 必要时存在 Agent 公钥
```

---

## 16. 核心原则

```text
私钥 = 身份凭证
公钥 = 授权记录
authorized_keys = 谁可以登录我
SSH Config = 我要如何连接别人
```

牢记：

1. 私钥不离开所属设备。
2. 公钥才用于分发。
3. 每个独立主体使用独立密钥。
4. Agent 权限遵循最小权限原则。
5. 新 VM 优先通过 Cloud-Init 注入公钥。
6. 私钥必须有可靠的加密备份。
7. 服务器应该可以重建，配置和密钥管理体系不能依赖某一台服务器。