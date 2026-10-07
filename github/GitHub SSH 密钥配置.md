使用 SSH Key 可以让 Linux 服务器免用户名、密码或 PAT 访问 GitHub，适用于 `git clone`、`git pull`、`git push` 等操作。

### **1. 生成 SSH 密钥**

查看当前是否已有密钥：

```bash
ls -la ~/.ssh/
```

如果没有 `id_ed25519`，生成新的 Ed25519 密钥：

```bash
ssh-keygen -t ed25519 -C "agent"
```

默认保存位置：

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

其中：

- `id_ed25519`：私钥，**禁止泄露**
- `id_ed25519.pub`：公钥，可以添加到 GitHub

服务器用于自动化 Git 操作时，可以不设置 passphrase，生成过程中直接回车。

---

### **2. 获取 SSH 公钥**

```bash
cat ~/.ssh/id_ed25519.pub
```

输出类似：

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxxxxxxxxxxxxxxxxxxxxx agent
```

复制**完整的一行**。

---

### **3. 添加公钥到 GitHub**

进入：

**GitHub → Settings → SSH and GPG keys → New SSH key**

填写：

```text
Title: Agent Server
Key type: Authentication Key
Key: ssh-ed25519 AAAAC3... agent
```

然后点击：

```text
Add SSH key
```

SSH Key 管理地址：

https://github.com/settings/keys

---

### **4. 测试 GitHub SSH 连接**

```bash
ssh -T git@github.com
```

第一次连接可能提示：

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

确认 GitHub 官方公布的主机指纹无误后输入：

```text
yes
```

认证成功会显示类似：

```text
Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.
```

这是**正常结果**，说明 SSH 认证成功。

---

### **5. GitHub SSH 使用 443 端口**

如果网络环境、代理或防火墙无法正常访问 SSH `22` 端口，可以使用 GitHub 提供的 SSH over HTTPS port。

先测试：

```bash
ssh -T -p 443 git@ssh.github.com
```

如果成功，编辑：

```bash
vim ~/.ssh/config
```

添加：

```sshconfig
Host github.com
    HostName ssh.github.com
    User git
    Port 443
```

设置权限：

```bash
chmod 600 ~/.ssh/config
```

再次测试：

```bash
ssh -T git@github.com
```

之后访问：

```text
git@github.com
```

实际上会连接：

```text
ssh.github.com:443
```

如果使用 Clash/Mihomo 的 TUN + Fake-IP 模式，解析 GitHub 时看到 `198.18.x.x` 不一定是异常。`198.18.0.0/15` 常被 Fake-IP 模式使用。

---

### **6. 将 Git 仓库从 HTTPS 改为 SSH**

查看当前远程仓库：

```bash
git remote -v
```

HTTPS 地址通常类似：

```text
https://github.com/<username>/<repository>.git
```

修改为 SSH：

```bash
git remote set-url origin git@github.com:<username>/<repository>.git
```

例如：

```bash
git remote set-url origin git@github.com:hybinlab/obsidian-vault.git
```

再次检查：

```bash
git remote -v
```

应该显示：

```text
origin  git@github.com:hybinlab/obsidian-vault.git (fetch)
origin  git@github.com:hybinlab/obsidian-vault.git (push)
```

之后即可：

```bash
git pull
git push
```

无需再输入 GitHub 用户名和 PAT。

---

### **7. 配置 Git Commit 身份**

SSH Key 只负责 GitHub **身份认证和仓库访问权限**。

Git Commit 还需要单独配置作者信息：

```bash
git config --global user.name "<GitHub用户名>"
git config --global user.email "<GitHub邮箱>"
```

例如：

```bash
git config --global user.name "hybinlab"
git config --global user.email "<GitHub noreply邮箱>"
```

如果不希望 Commit 暴露真实邮箱，可以在 GitHub：

**Settings → Emails**

查看 GitHub 提供的 `noreply` 邮箱。

检查配置：

```bash
git config --global --list
```

---

### **常用排查命令**

查看 SSH 文件：

```bash
ls -la ~/.ssh/
```

查看公钥：

```bash
cat ~/.ssh/id_ed25519.pub
```

测试 GitHub SSH：

```bash
ssh -T git@github.com
```

详细查看 SSH 连接过程：

```bash
ssh -vT git@github.com
```

查看远程仓库：

```bash
git remote -v
```

查看 Git 身份：

```bash
git config --global user.name
git config --global user.email
```

查看当前 Git 配置：

```bash
git config --list
```

### **注意事项**

1. **不要上传或分享** **`~/.ssh/id_ed25519`** **私钥。**
2. GitHub SSH 公钥应添加 `.pub` 文件内容。
3. 每台长期使用的服务器建议生成自己的 SSH Key，不要到处复制同一份私钥。
4. 删除服务器或服务器失去控制后，应及时在 GitHub 删除对应 SSH Key。
5. SSH Key 与 Git Commit 的 `user.name/user.email` 是两套独立机制。
6. GitHub HTTPS Git 操作不支持账户密码认证；HTTPS 应使用 PAT，或者直接改用 SSH。