---
publish: true
---
## Ansible Vault 加密敏感数据

`ansible-vault` 用于加密 Playbook、变量文件中的敏感数据（密码、API 密钥、证书等），使其可以安全地纳入版本控制（Git）。

> **要不要用？** 如果不打算把 playbook 推到公开/共享仓库，直接用 `.gitignore` 排除含密码的变量文件更省事。团队协作、代码需要提交到共享仓库时才是刚需。企业环境常改用 CI/CD 平台自带的 Secret 注入（GitHub Actions/GitLab CI）或 AWX/AAP 的 Credential 管理来代替。详见 [[ansible/Ansible 概念.md]] 中的实战判断。

## 核心概念

- **加密对象**：可以是整个文件，也可以是文件中的单个变量（局部加密，其余明文可读）
- **密钥（Vault Password）**：一个密码/密钥文件，用来加解密内容；同一个密码才能解开对应加密的内容
- **Vault ID**：给密钥起的身份标签，支持多个密钥并存（比如 `dev`、`prod` 用不同密钥），适合分级权限管理

## 7 个子命令

|子命令|作用|
|---|---|
|create|创建一个新文件，在编辑器中写内容，保存关闭后自动加密|
|edit|打开已加密文件（自动解密到编辑器），保存关闭后重新加密|
|view|只读查看加密文件内容（不落地明文）|
|encrypt|加密一个已存在的明文文件|
|decrypt|解密一个已加密文件（生成明文）|
|encrypt_string|加密单个字符串，用于局部加密某个变量|
|rekey|用新密码重新加密（更换密钥）|

## 基本用法

### 创建/编辑加密文件

```bash
# 创建新的加密文件（会提示输入密码，然后打开编辑器）
ansible-vault create secrets.yml

# 编辑已有的加密文件
ansible-vault edit secrets.yml

# 只查看，不编辑
ansible-vault view secrets.yml
```

### 加密/解密已有文件

```bash
# 加密一个已存在的明文文件
ansible-vault encrypt vars/production.yml

# 解密回明文（谨慎使用，别忘了重新加密或删除明文）
ansible-vault decrypt vars/production.yml

# 加密后输出到指定文件（保留原文件不变）
ansible-vault encrypt vars/production.yml --output=vars/production.vault.yml
```

### 加密单个变量（局部加密）

最常用的场景：文件大部分是明文配置，只有密码字段需要加密。

```bash
# 加密一个字符串，生成可直接粘贴进 YAML 的密文块
ansible-vault encrypt_string 'my-secret-password' --name 'db_password'

# 输出示例：
# db_password: !vault |
#           $ANSIBLE_VAULT;1.1;AES256
#           66386439653236336462626566653063336164663966303231363934653561363537653464...
#
# 直接粘贴到 vars.yml 里，其他变量保持明文
```

```yaml
# vars.yml - 混合明文和加密变量
db_host: 192.168.10.30
db_port: 5432
db_user: admin
db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          66386439653236336462626566653063336164663966303231363934653561...
```

### 更换密钥

```bash
# 用新密码重新加密（会提示输入旧密码和新密码）
ansible-vault rekey secrets.yml
```

## 密码指定方式

不想每次手动输入密码，可以用密码文件或环境变量：

|方式|参数/配置|
|---|---|
|交互式输入|`-J` / `--ask-vault-password`（默认行为）|
|密码文件|`--vault-password-file=~/.vault_pass`|
|环境变量指定文件|`ANSIBLE_VAULT_PASSWORD_FILE=~/.vault_pass`|
|脚本动态获取密码|密码文件设为可执行脚本，输出密码到 stdout|

```bash
# 用密码文件，避免每次手动输入
echo 'mypassword' > ~/.vault_pass
chmod 600 ~/.vault_pass

ansible-vault view secrets.yml --vault-password-file=~/.vault_pass

# 配置到 ansible.cfg，一劳永逸
# vault_password_file = ~/.vault_pass
```

> 密码文件本身也是敏感数据，注意权限（600）和 `.gitignore`。

## 多密钥管理（Vault ID）

场景：`dev` 环境和 `prod` 环境用不同密钥，避免开发人员能解密生产密码。

```bash
# 用 dev 身份加密开发环境变量
ansible-vault encrypt --vault-id dev@prompt vars/dev.yml

# 用 prod 身份加密生产环境变量（用密码文件）
ansible-vault encrypt --vault-id prod@~/.vault_pass_prod vars/prod.yml

# 执行 playbook 时提供所有需要的密钥
ansible-playbook site.yml \
  --vault-id dev@prompt \
  --vault-id prod@~/.vault_pass_prod
```

## 在 Playbook 中使用

`ansible-playbook` 执行含加密内容的 playbook 时，透明解密，不需要额外代码改动：

```bash
# 提示输入密码
ansible-playbook site.yml --ask-vault-pass

# 用密码文件
ansible-playbook site.yml --vault-password-file=~/.vault_pass

# 简写（部分版本支持）
ansible-playbook site.yml --vault-id @prompt
```

## 实战例子

### 例子1：分离敏感变量到独立文件

```
project/
├── site.yml
├── vars/
│   ├── main.yml          # 明文，正常提交 Git
│   └── secrets.yml       # 加密，可以安全提交 Git
```

```yaml
# site.yml
---
- hosts: all
  vars_files:
    - vars/main.yml
    - vars/secrets.yml
  tasks:
    - name: Configure database
      template:
        src: db_config.j2
        dest: /etc/app/db.conf
      # db.conf 模板里引用 secrets.yml 中的 db_password 变量
```

```bash
# 创建加密的 secrets.yml
ansible-vault create vars/secrets.yml
# 编辑器中输入：
# db_password: supersecret123

# 执行 playbook
ansible-playbook site.yml --ask-vault-pass
```

### 例子2：Git 提交前检查

```bash
# 确保不会误提交明文密码
git diff vars/secrets.yml
# 应该只看到密文块变化，而非明文

# .gitignore 里排除密码文件本身（不是加密后的 yml）
echo '.vault_pass' >> .gitignore
```

## 局限性和替代方案

- **密钥轮换麻烦**：改一次密码要 `rekey` 所有相关文件
- **diff 不友好**：Git diff 只能看到密文变化，看不出实际改了什么内容
- **密钥分发问题**：Vault 本身不解决"如何安全地把密码分发给团队成员"这个问题

常见替代/补充方案：
- CI/CD 平台自带 Secret（GitHub Actions Secrets、GitLab CI Variables）
- AWX / Ansible Automation Platform 的 Credential 管理
- 外部密钥管理服务：HashiCorp Vault（另一个产品，勿与 Ansible Vault 混淆）、AWS Secrets Manager

## 提示

- 局部加密（`encrypt_string`）优于整文件加密，方便 code review 时看清哪些是敏感数据
- 密码文件要设权限 `600`，并加入 `.gitignore`
- 团队协作用 Vault ID 分级，避免所有人共用一个密钥
- 定期 `rekey`，尤其在团队成员离职后
