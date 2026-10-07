---
publish: true
---
> 日期：2026-09-01 环境：Ubuntu 目标：在 Ubuntu 上通过 pipx 全局安装 ansible-core

---

##  安装步骤

### #1. 安装 pipx（系统包管理器）

``` bash

sudo apt update

sudo apt install pipx

pipx ensurepath
```

### #2. 安装 ansible-core

```bash

pipx install ansible-core
```

### #3. 验证安装

```bash

ansible --version
```

输出示例：

```bash
ansible [core 2.21.3]
  config file = None
  configured module search path = ['/root/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /root/.local/share/pipx/venvs/ansible-core/lib/python3.12/site-packages/ansible
  ansible collection location = /root/.ansible/collections:/usr/share/ansible/collections
  executable location = /root/.local/bin/ansible
  python version = 3.12.3
```

### #4. 验证 SSH 连通性

```bash

ssh -i ~/.ssh/homelab_ed25519 root@192.168.31.1 "echo ok"
```

---

## 注意事项

- **不要安装** `**ansible**` **元包**：PyPI 上的 `ansible` 包只暴露 `ansible-community`，实际 CLI 工具在 `ansible-core` 里
    
- **不要用** `**pip install ansible**`：会装元包，且可能污染系统 Python 环境
    
- **pipx 管理**：pipx 本身由 apt 安装，ansible-core 由 pipx 管理，隔离且可卸载
    

---

## 卸载
```bash

pipx uninstall ansible-core

sudo apt remove pipx
```
---

## 扩展：安装社区模块（如需）

```bash

ansible-galaxy collection install community.general
```

