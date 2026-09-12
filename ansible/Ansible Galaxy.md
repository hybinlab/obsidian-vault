---
publish: true
---
## ansible-galaxy 角色和集合管理

`ansible-galaxy` 是管理 Ansible **角色（Roles）** 和 **集合（Collections）** 的命令行工具。用于搜索、安装、创建和发布可复用的 Ansible 组件，避免重复造轮子。

## 核心概念

### Role（角色）
- 结构化的 Playbook 组织方式，包含任务、处理程序、变量、文件、模板等
- 便于代码复用，如 "安装 Nginx" 可以作为一个可复用角色
- 从 Galaxy 市场下载或自己创建

### Collection（集合）
- Ansible 2.9+ 引入，是较新的内容分发格式
- 包含多个模块、插件、角色、Playbook 等
- 官方和社区都在逐步迁移到 Collection

## Role 命令

### 创建角色

```bash
# 在当前目录创建角色框架
ansible-galaxy role init my-nginx

# 指定目录位置
ansible-galaxy role init -p ./roles my-apache
```

创建的目录结构：
```
my-nginx/
├── README.md
├── defaults/           # 默认变量
├── files/             # 静态文件
├── handlers/          # 处理程序
├── meta/              # 角色元数据
├── tasks/             # 任务
├── templates/         # Jinja2 模板
├── tests/             # 测试 playbook
└── vars/              # 变量
```

### 安装角色

```bash
# 从 Galaxy 安装单个角色
ansible-galaxy role install geerlingguy.nodejs

# 安装指定版本
ansible-galaxy role install geerlingguy.nodejs,2.0.0

# 从 requirements.yml 批量安装
ansible-galaxy role install -r requirements.yml

# 指定安装目录
ansible-galaxy role install -p ./roles geerlingguy.nginx

# 强制覆盖已有角色
ansible-galaxy role install -f geerlingguy.nodejs
```

### requirements.yml 格式

```yaml
---
- name: geerlingguy.nodejs
  version: 2.0.0

- name: geerlingguy.nginx
  src: https://github.com/geerlingguy/ansible-role-nginx.git
  scm: git
  version: master

- name: geerlingguy.docker
  version: 4.0.0
```

### 其他 Role 命令

```bash
# 列出已安装角色
ansible-galaxy role list

# 查看角色信息
ansible-galaxy role info geerlingguy.nodejs

# 删除角色
ansible-galaxy role remove geerlingguy.nodejs

# 在 Galaxy 上搜索角色
ansible-galaxy role search nginx

# 从 GitHub 导入角色到 Galaxy（需认证）
ansible-galaxy role import username/repo

# 从 Galaxy 删除自己的角色（需认证）
ansible-galaxy role delete username/role-name
```

## Collection 命令

### 创建集合

```bash
# 创建集合框架
ansible-galaxy collection init my_company.my_collection

# 指定目录
ansible-galaxy collection init -p ./collections my_company.my_collection
```

创建的目录结构：
```
my_company/my_collection/
├── README.md
├── galaxy.yml           # 集合元数据
├── plugins/             # 模块、插件
│   ├── modules/
│   ├── filters/
│   └── ...
├── roles/               # 可选的角色
├── playbooks/           # Playbook 示例
└── tests/               # 测试
```

### 构建和发布集合

```bash
# 构建集合（生成 .tar.gz 文件）
ansible-galaxy collection build

# 构建到指定目录
ansible-galaxy collection build -o ./dist/

# 发布到 Galaxy（需 API Token）
ansible-galaxy collection publish ./my_company-my_collection-1.0.0.tar.gz --api-key=your_api_token
```

### 安装集合

```bash
# 从 Galaxy 安装单个集合
ansible-galaxy collection install community.general

# 安装指定版本
ansible-galaxy collection install community.general:5.0.0

# 从 requirements.yml 批量安装
ansible-galaxy collection install -r requirements.yml

# 指定安装目录
ansible-galaxy collection install -p ./collections community.general

# 跳过依赖安装
ansible-galaxy collection install --no-deps community.general
```

### Collection requirements.yml 格式

```yaml
---
collections:
  - name: community.general
    version: ">=5.0.0"

  - name: cloud.terraform
    version: 2.0.0

  - name: ansible.posix
```

### 其他 Collection 命令

```bash
# 列出已安装集合
ansible-galaxy collection list

# 验证已安装集合的完整性
ansible-galaxy collection verify

# 下载集合到本地（离线部署）
ansible-galaxy collection download community.general -p ./collections

# 查看集合详情
ansible-galaxy collection info community.general
```

## 常用参数

|参数|功能|
|---|---|
|-p / --path|指定角色/集合安装目录|
|-r / --requirements-file|从文件读取安装列表（requirements.yml）|
|-f / --force|强制覆盖已有的文件|
|-n / --no-deps|跳过依赖安装（仅安装指定项）|
|-s / --server|指定 Galaxy API 服务器地址|
|--timeout|设置服务器操作超时（默认60秒）|
|--token / --api-key|提供认证令牌（用于发布）|

## 实战例子

### 场景1：快速部署开源角色

```bash
# 创建 requirements.yml
cat > requirements.yml << EOF
---
- name: geerlingguy.nodejs
  version: 2.0.0

- name: geerlingguy.nginx
  version: 4.0.0
EOF

# 安装所有依赖角色
ansible-galaxy role install -r requirements.yml

# 在 Playbook 中使用
cat > site.yml << EOF
---
- hosts: all
  roles:
    - geerlingguy.nodejs
    - geerlingguy.nginx
EOF

ansible-playbook site.yml
```

### 场景2：创建和发布自己的集合

```bash
# 1. 创建集合框架
ansible-galaxy collection init mycompany.custom_collection

# 2. 编写模块、插件、角色
cd mycompany/custom_collection
# 在 plugins/modules/ 添加自定义模块
# 在 roles/ 添加角色
# ...

# 3. 构建
ansible-galaxy collection build

# 4. 发布（需在 Galaxy 网站获取 API Token）
ansible-galaxy collection publish mycompany-custom_collection-1.0.0.tar.gz \
  --api-key=glkc_xxx...
```

### 场景3：离线部署

```bash
# 在有网络的机器上下载集合
ansible-galaxy collection download -p ./collections -r requirements.yml

# 打包所有下载的集合
tar -czf ansible-collections.tar.gz collections/

# 在无网络的机器上解压和安装
tar -xzf ansible-collections.tar.gz
ansible-galaxy collection install -p ./collections -r requirements.yml --no-deps
```

## Role vs Collection

| 特性 | Role | Collection |
|------|------|-----------|
| 推出版本 | 2.0+ | 2.9+ |
| 存储格式 | 目录 | .tar.gz |
| 包含内容 | 任务、处理程序、变量、文件等 | 模块、插件、角色、Playbook |
| 发展趋势 | 逐步淘汰 | 官方推荐 |
| 安装来源 | Galaxy、GitHub、本地 | Galaxy、GitHub、本地 |

## 常见工作流

1. **查找现有组件**：`ansible-galaxy role search` / 搜索 Galaxy 网站
2. **安装依赖**：`ansible-galaxy role/collection install -r requirements.yml`
3. **创建 Playbook**：编写 playbook 引用已安装的角色/集合
4. **分享代码**：`ansible-galaxy role/collection init` → 开发 → 发布

## 提示

- **Ansible Galaxy 网站**：https://galaxy.ansible.com 可视化搜索和浏览
- **版本管理**：在 requirements.yml 中指定版本，避免破坏性更新
- **离线部署**：使用 `collection download` 预下载，便于无网络环境部署
- **依赖关系**：通过 `galaxy.yml` 或角色的 `meta/main.yml` 声明依赖
