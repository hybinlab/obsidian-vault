---
tags:
  - ansible
  - 排障
publish: true
---
# Ansible pipx 安装踩坑记录


> 日期：2026-09-01 背景：在 VM 上安装 ansible 过程中的实际问题

---

## 问题一：ansible 元包只暴露 ansible-community

**现象**：`pipx install ansible` 安装成功，但 `which ansible` 无输出，只有 `ansible-community` 命令可用。

**原因**：PyPI 上的 `ansible` 包是一个元包（meta-package），实际的 CLI 工具（`ansible`、`ansible-playbook` 等）在 `ansible-core` 里。pipx 默认只暴露元包顶层声明的 entry point，所以只出来个 `ansible-community`。

**解决**：`pipx uninstall ansible && pipx install ansible-core`

`ansible-core` 才是真正包含所有 CLI 工具的包。安装完成后暴露：

- `ansible`
    
- `ansible-config`
    
- `ansible-console`
    
- `ansible-doc`
    
- `ansible-galaxy`
    
- `ansible-inventory`
    
- `ansible-playbook`
    
- `ansible-pull`
    
- `ansible-test`
    
- `ansible-vault`
---

## 问题二：用 python3 -m pip 安装 pipx 本身

**现象**：第一次安装时用 `python3 -m pip install pipx` 装 pipx，再用 pipx 装 ansible。

**原因**：PEP 668（Exterior Pinned Python Environments）机制下，现代 Debian/Ubuntu 会直接拒绝 `pip install xxx`（无参数）的系统级安装，除非加 `--break-system-packages`。如果用 `pip install --user pipx`，则安装到用户目录，不算污染系统环境，只是不如 apt 管理得干净。

**正确做法**：`sudo apt install pipx && pipx ensurepath && pipx install ansible-core`

---

## 问题三：补 symlink 是错误思路

**现象**：发现 pipx 只暴露了 `ansible-community`，`ansible` 命令缺失。

**错误思路**：尝试手动 `ln -s` 补 symlink 到 `/usr/local/bin/`。

**原因**：这是系统级配置修改，且是 hack 方式。问题的根源是包的选择错误，不是缺少 symlink。

**正确做法**：从根源解决，换 `ansible-core` 包。

---

## 总结

|步骤|正确做法|
|---|---|
|1|`sudo apt install pipx`（系统包管理器安装 pipx）|
|2|`pipx ensurepath`（确保 pipx 的 PATH 已配置）|
|3|`pipx install ansible-core`（安装 ansible-core 而非 ansible 元包）|
|4|验证：`which ansible && ansible --version`|

**补充**：`ansible-core` 只包含内置模块（`ansible.builtin.*`），社区模块（如 `community.general`、`amazon.aws`）不在其中，后续如需用到，用 `ansible-galaxy collection install` 单独安装。

---

## 经验

- Ansible 不要装 `ansible` 元包，要装 `ansible-core`
    
- pipx 是隔离工具，装 pipx 本身也要走系统包管理器
    
- 遇到问题先找根源，不要用 hack 绕过去
